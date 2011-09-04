"""
*                   Any node                                                                                    1
T                   A node of type T, where T is one string, number, object, array, boolean, or null            1
T.key               A node of type T which is the child of an object and is the value its parents key property  1
T."complex key"     Same as previous, but with property name specified as a JSON string                         1
T:root              A node of type T which is the root of the JSON document                                     1
T:nth-child(n)      A node of type T which is the nth child of an array parent                                  1
T:nth-last-child(n) A node of type T which is the nth child of an array parent counting from the end            2
T:first-child       A node of type T which is the first child of an array parent                                1
T:last-child        A node of type T which is the last child of an array parent                                 2
T:only-child        A node of type T which is the only child of an array parent                                 2
T:empty             A node of type T which is an array or object with no child                                  2
T U                 A node of type U with an ancestor of type T                                                 1
T > U               A node of type U with a parent of type T                                                    1
T ~ U               A node of type U with a sibling of type T                                                   2
S1, S2              Any node which matches either selector S1 or S2                                             1
T:has(S)            A node of type T which has a child node satisfying the selector S                           3
T:expr(E)           A node of type T with a value that satisfies the expression E                               3
T:val(V)            A node of type T with a value that is equal to V                                            3
T:contains(S)       A node of type T with a string value contains the substring S                               3
"""
"""
jsonselect


Public interface:
    select
    take a selector and an object. return matched node(s)

Exceptions:
    SelectorSyntaxError
    Raised by Parser when parsing cannot continue. 

"""
import re
import numbers
import collections
import functools
import logging


S_TYPE = lambda x, token: ('type', token)
S_IDENTIFIER = lambda x, token: ('identifier', token[1:])
S_QUOTED_IDENTIFIER = lambda x, token: S_IDENTIFIER(None,
                                                    token.replace('"', ''))
S_PCLASS = lambda x, token: ('pclass', token[1:])
S_PCLASS_FUNC = lambda x, token: ('pclass_func', token[1:])
S_OPER = lambda x, token: ('operator', token)
S_EMPTY = lambda x, token:  ('empty', ' ')
S_UNK = lambda x, token: ('unknown', token)
S_INT = lambda x, token: ('int', int(token))
S_FLOAT = lambda x, token: ('float', float(token))
S_WORD = lambda x, token: ('word', token)
S_BINOP = lambda x, token: ('binop', token)
S_VALS = lambda x, token: ('val', token)
S_KEYWORD = lambda x, token: ('keyword', token)
S_VAR = lambda x, token: ('var', token)

SCANNER = re.Scanner([
    (r"[~*,>\)\(]", S_OPER),
    (r"\s", S_EMPTY),
    (r"(-?\d+(\.\d*)([eE][+\-]?\d+)?)", S_FLOAT),
    (r"\d+", S_INT),
    (r"string|boolean|null|array|object|number", S_TYPE),
    (r'\.?\"([^"\\]|\\[^"])*\"', S_QUOTED_IDENTIFIER),
    (u"\.([_a-zA-Z]|[^\0-\0177]|\\[^\s0-9a-fA-F])(?:[_a-zA-Z0-9\-]" \
     u"|[^\u0000-\u0177]|(?:\\[^\s0-9a-fA-F]))*", S_IDENTIFIER),
    (r":(root|first-child|last-child|only-child)", S_PCLASS),
    (r":(nth-child|nth-last-child|has|expr|val|contains)", S_PCLASS_FUNC),
    (r"(&&|\|\||[\$\^<>!\*]=|[=+\-*/%<>])", S_BINOP),
    (r"true|false|null", S_VALS),
    (r"n", S_VAR),
    (r"odd|even", S_KEYWORD),
    (r"\w+", S_WORD),
])

log = logging.getLogger(__name__)


class SelectorSyntaxError(Exception):
    pass


def lex(selector):
    tokens, rest = SCANNER.scan(selector)
    if not len(tokens):
        if rest:
            raise Exception("leftover input: %s" % rest)
    return [tok for tok in tokens if tok[0] != 'empty']

# metadata about a node in the target object graph
Node = collections.namedtuple('Node', [
    'value',
    'parent',       # parent Node. None if root.
    'parent_key',   # if parent is a dict, key which indexes current Node.
    'idx',          # if parent is an array, index of curr Node. starts at 1.
    'siblings'      # if parent is an array, list of sibling Nodes.
])


def object_iter(obj, parent=None, parent_key=None, idx=None,
                siblings=None):
    """
    Yields each node of object graph in postorder
    """

    obj_node = Node(value=obj, parent=parent, parent_key=parent_key,
                siblings=siblings, idx=idx)

    if isinstance(obj, list):
        _siblings = len(obj)
        for i, elem in enumerate(obj):
            for node in object_iter(elem, obj_node, None, i + 1, _siblings):
                yield node
    elif isinstance(obj, collections.Mapping):
        for key in obj:
            for node in object_iter(obj[key], obj_node, key):
                yield node
    yield obj_node


class Parser(object):

    """
    Parse jsonselect queries.
    
    A simple top-down recursive-descendent parser of jsonselect selectors.
    Initialize with the object you wish to match against.

    Clients should only need to call Parser.parse, which accepts
    a list of tokens as generated by jsonselect.lex
    """

    def __init__(self, obj):
        """Create a parser for a particular object."""
        self.obj = obj

    def parse(self, tokens):
        """Accept a list of tokens. Returns matched nodes of self.obj."""
        log.debug(self.obj)

        if self.peek(tokens, 'operator') == '*':
            self.match(tokens, 'operator')
            results = list(object_iter(self.obj))
        else:
            results = self.selector_production(tokens)

        results = [node.value for node in results]
        # single results should be returned as a primitive
        if len(results) == 1:
            return results[0]
        return results

    def selector_production(self, tokens):
        """Production for a full selector."""

        log.debug(tokens)
        validators = []
        # productions should add their own nodes to the found list

        if self.peek(tokens, 'type'):
            type_ = self.match(tokens, 'type')
            validators.append(self.type_production(type_))

        if self.peek(tokens, 'identifier'):
            key = self.match(tokens, 'identifier')
            validators.append(self.key_production(key))

        if self.peek(tokens, 'pclass'):
            pclass = self.match(tokens, 'pclass')
            validators.append(self.pclass_production(pclass))

        if self.peek(tokens, 'pclass_func'):
            pclass_func = self.match(tokens, 'pclass_func')
            validators.append(self.pclass_func_production(pclass_func, tokens))

        # apply validators from a selector expression to self.obj
        results = self._eval(validators, self.obj)

        if self.peek(tokens, 'operator'):
            operator = self.match(tokens, 'operator')
            rvals = self.selector_production(tokens)
            if operator == ',':
                results.extend(rvals)
            elif operator == '>':
                results = self.parents(results, rvals)
            elif operator == '~':
                results = self.siblings(results, rvals)
                return results
        else:
            if len(tokens):
                rvals = self.selector_production(tokens)
                results = self.ancestors(results, rvals)

        return results

    def parents(self, lhs, rhs):
        """Find nodes in rhs which have parents in lhs."""

        return [node for node in rhs if node.parent in lhs]

    def ancestors(self, lhs, rhs):
        """Return nodes from rhs which have ancestors in lhs."""

        def _search(node):
            if node in lhs:
                return True
            if not node.parent:
                return False
            return _search(node.parent)

        return [node for node in rhs if _search(node)]

    def siblings(self, lhs, rhs):
        """Find nodes in rhs having common parents in lhs."""
        parents = [node.parent for node in lhs]

        return [node for node in rhs if node.parent in parents]

    # The following productions should return predicate functions

    def type_production(self, type_):
        assert type_

        type_map = {
            'string': basestring,
            'number': numbers.Number,
            'object': collections.Mapping,
            'array': list,
            'boolean': bool,
            'null': type(None)
        }
        return lambda node: isinstance(node.value, type_map[type_])

    def key_production(self, key):
        assert key

        def validate(node):
            if not node.parent_key:
                return False
            return node.parent_key == key
        return validate

    def pclass_production(self, pclass):

        if pclass == 'first-child':
            return lambda node: node.idx == 1
        elif pclass == 'last-child':
            return lambda node: \
                node.siblings and node.idx == node.siblings
        elif pclass == 'only-child':
            return lambda node: node.siblings == 1
        elif pclass == 'root':
            return lambda node: not node.parent
        else:
            raise Exception("unrecognized pclass %s" % pclass)

    def parse_pclass_func_args(self, tokens):
        """Parse arguments to a psuedoclass function.

        Raises SelectorSyntaxError if bad arguments found.
        """
        expected = ['int', 'binop', 'float', 'var', 'keyword', 'operator']
        args = []

        if self.peek(tokens, 'operator') == '(':
            args.append(tokens.pop(0))
        else:
            raise SelectorSyntaxError()

        while tokens:
            if self.peek(tokens, 'operator') == '(':
                args.extend(self.parse_pclass_func_args(tokens))
            elif self.peek(tokens, 'operator') == ')':
                break
            # TODO: operators should maybe be parsed seperately.
            # Wouldn't expect to see operator tokens here.
            elif self.peek(tokens, expected):
                args.append(tokens.pop(0))
                continue
            else:
                raise SelectorSyntaxError()
        else:
            raise SelectorSyntaxError()

        if self.peek(tokens, 'operator') == ')':
            args.append(tokens.pop(0))
        else:
            raise SelectorSyntaxError()

        return args

    def pclass_func_production(self, lexeme, tokens):
        """Parse args and pass them to pclass_func_validator."""

        args = self.parse_pclass_func_args(tokens)
        return functools.partial(self.pclass_func_validator, lexeme, args)

    def pclass_func_validator(self, pclass, args, node):
        """Predicate function for psuedoclass functions.
        
        Raises SelectorSyntaxError if unrecognized psuedoclass function.
        """

        if pclass == 'nth-child':
            if not node.siblings:
                return False
            return self.eval_args(args, node.idx)
        elif pclass == 'nth-last-child':
            if not node.siblings:
                return False
            reverse_idx = node.siblings - (node.idx - 1)
            return self.eval_args(args, reverse_idx)
        else:
            raise SelectorSyntaxError()

    @staticmethod
    def eval_args(args, n=None):
        """Evaluate a list of tokens.

        return a validator (callable), which accepts 1 argument
        and return True or False.
        """

        expr_str = ''.join([str(arg[1]) for arg in args])

        local_vars = {
            'odd': lambda idx: idx % 2 == 1,
            'even': lambda idx: idx % 2 == 0,
            'n': n
        }

        ret = eval(expr_str, None, local_vars)
        if callable(ret):
            return ret(n)
        elif len([x for x in args if x[0] == 'var']):
            return ret >= 0
        else:
            return ret == n

    def _eval(self, validators, obj):
        """Apply each validator in validators to each node in obj.

        Return each node in obj which matches all validators.
        """

        results = []
        for node in object_iter(obj):
            if all([validate(node) for validate in validators]):
                results.append(node)
        return results

    @staticmethod
    def match(tokens, type_):
        if not Parser.peek(tokens, type_):
            raise Exception('match not successful')

        token = tokens.pop(0)
        return token[1]

    @staticmethod
    def peek(tokens, type_):
        if not tokens:
            return False

        if isinstance(type_, list) and tokens[0][0] in type_:
            return tokens[0][1]
        elif tokens[0][0] == type_:
            return tokens[0][1]
        else:
            return False


def select(selector, obj):
    """Appy selector to obj and return matching nodes.
    
    If only one node is found, return it, otherwise return a list of matches.
    Returns False on syntax error. None if no results found.
    """

    parser = Parser(obj)
    try:
        return parser.parse(lex(selector))
    except SelectorSyntaxError:
        return False
