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


IDEA:

    each production returns a list of matching nodes. Do set arithmetic at higher levels?
    This might work because we'll be working with Nodes and not primitives

    i.e.
    expr_prod:
        and(results, type_prod)
        and(results, id_prod)
        and(results, pclass_prod)
        if next == ','
            or(results, expr_prod)
        if next == ' '
            ancestor(results, expr_prod)
        if next == '~':
            sibling(results, expr_prod)
        if next == '>'
            parent(results, expr_prod)
        return results

    might be hard to do set arithmetic because node.value could be an unhashable primitive.
    perhaps going back to adding validators.
    or a hybrid approach where and/or adds validators
"""
import re
import numbers
import collections
import functools


S_TYPE = lambda x, token: ('type', token)
S_IDENTIFIER = lambda x, token: ('identifier', token[1:])
S_QUOTED_IDENTIFIER = lambda x, token: S_IDENTIFIER(None, token.replace('"', ''))
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


class SelectorSyntaxError(Exception): pass

def lex(selector):
    tokens, rest = SCANNER.scan(selector)
    if not len(tokens):
        if rest:
            raise Exception("leftover input: %s" % rest)
    return tokens

# sibling_idx is 1 indexed
# parents is a list of nodes from current node to root.
Node = collections.namedtuple('Node', ['value', 'parent', 'parent_key',
                                       'sibling_idx', 'siblings'])

def object_iter(obj, parent=None, parent_key=None, sibling_idx=None, siblings=None):
    """
    Yields each node of object graph in postorder
    """

    obj_node = Node(value=obj, parent=parent, parent_key=parent_key,
                siblings=siblings, sibling_idx=sibling_idx)

    if isinstance(obj, list):
        _siblings = len(obj)
        for i, elem in enumerate(obj):
            for node in object_iter(elem, obj_node, None, i+1, _siblings):
                yield node
    elif isinstance(obj, collections.Mapping):
        for key in obj:
            for node in object_iter(obj[key], obj_node, key):
                yield node
    yield obj_node


class Parser(object):

    def __init__(self, obj):
        self.obj = obj

    def _eval(self, validators, obj):
        results = []
        for node in object_iter(obj):
            if all([validate(node) for validate in validators]):
                results.append(node)
        return results

    def parse(self, tokens):
        print self.obj

        if self._peek(tokens, 'operator') == '*':
            self._match(tokens, 'operator')
            return [node.value for node in object_iter(self.obj)]
        else:
            results = self.selector_production(tokens)
            results = [node.value for node in results]
            # single results should be returned as a primitive
            if len(results) == 1:
                return results[0]
            return results

    def selector_production(self, tokens):

        print tokens
        validators = []
        # productions should add their own nodes to the found list
        if self._peek(tokens, 'type'):
            type_ = self._match(tokens, 'type')
            validators.append(self.type_production(type_))

        if self._peek(tokens, 'identifier'):
            key = self._match(tokens, 'identifier')
            validators.append(self.key_production(key))

        if self._peek(tokens, 'pclass'):
            pclass = self._match(tokens, 'pclass')
            validators.append(self.pclass_production(pclass))

        if self._peek(tokens, 'pclass_func'):
            pclass_func = self._match(tokens, 'pclass_func')
            validators.append(self.pclass_func_production(pclass_func, tokens))

        results = self._eval(validators, self.obj)

        if self._peek(tokens, 'operator'):
            operator = self._match(tokens, 'operator')
            rvals = self.selector_production(tokens)
            if operator == ',':
                results.extend(rvals)
            elif operator == '>':
                results = self.parents(results, rvals)
            elif operator == '~':
                results = self.siblings(results, rvals)
        elif self._peek(tokens, 'empty'):
            self._match(tokens, 'empty')
            rvals = self.selector_production(tokens)
            results = self.ancestors(results, rvals)

        return results

    def parents(self, lhs, rhs):
        pass

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
        pass

    def type_production(self, type_):
        assert type_

        map = {
            'string': basestring,
            'number': numbers.Number,
            'object': collections.Mapping,
            'array': list,
            'boolean': bool,
            'null': type(None)
        }
        return lambda node: isinstance(node.value, map[type_])


    def key_production(self, key):
        assert key

        def validate(node):
            if not node.parent_key:
                return False
            return node.parent_key == key
        return validate


    def pclass_production(self, pclass):

        if pclass == 'first-child':
            return lambda node: node.sibling_idx == 1
        elif pclass == 'last-child':
            return lambda node: \
                node.siblings and node.sibling_idx == node.siblings
        elif pclass == 'only-child':
            return lambda node: node.siblings == 1
        elif pclass == 'root':
            return lambda node: not node.parent
        else:
            raise Exception("unrecognized pclass %s" % pclass)


    def parse_pclass_func_args(self, tokens):
        """Make sure that tokens in a well-formed argument list."""
        args = []

        if self._peek(tokens, 'operator') == '(':
            args.append(tokens.pop(0))
        else:
            raise SelectorSyntaxError()

        while tokens:
            if self._peek(tokens, 'operator') == '(':
                args.extend(self.parse_pclass_func_args(tokens))
            elif self._peek(tokens, 'operator') == ')':
                break
            # TODO: operators should maybe be parsed seperately.
            # Wouldn't expect to see operator tokens here.
            elif self._peek(tokens, ['int', 'binop', 'float', 'var', 'keyword', 'empty', 'operator']):
                args.append(tokens.pop(0))
                continue
            else:
                raise SelectorSyntaxError()
        else:
            raise SelectorSyntaxError()

        if self._peek(tokens, 'operator') == ')':
            args.append(tokens.pop(0))
        else:
            raise SelectorSyntaxError()

        return args


    def eval_args(self, args, n=None):
        """Evaluate a list of tokens.

        return a validator (callable), which accepts 1 argument
        and return True or False."""

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

    def pclass_func_production(self, lexeme, tokens):
        """
        Parse args and pass them to pclass_function_validator.
        """

        args = self.parse_pclass_func_args(tokens)
        return functools.partial(self.pclass_function_validator, lexeme, args)

    def pclass_function_validator(self, pclass, args, node):
        if pclass == 'nth-child':
            if not node.siblings:
                return False
            return self.eval_args(args, node.sibling_idx)
        elif pclass == 'nth-last-child':
            if not node.siblings:
                return False
            reverse_idx = node.siblings - (node.sibling_idx - 1)
            return self.eval_args(args, reverse_idx)
        else:
            raise SelectorSyntaxError()

    def _match(self, tokens, type_):
        if not self._peek(tokens, type_):
            raise Exception('match not successful')

        t = tokens.pop(0)
        return t[1]

    def _match_any(self, tokens):
        t = tokens.pop(0)
        return t[1]

    def _peek(self, tokens, type_):
        if not tokens:
            return False

        if isinstance(type_, list) and tokens[0][0] in type_:
            return tokens[0][1]
        elif tokens[0][0] == type_:
            return tokens[0][1]
        else:
            return False

def select(selector, obj):
    parser = Parser(obj)
    return parser.parse(lex(selector))
