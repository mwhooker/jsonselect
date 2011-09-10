"""
jsonselect


Public interface:
    select
    take a selector and an object. return matched node(s)

Exceptions:
    SelectorSyntaxError
    Raised by Parser when parsing cannot continue.

TODO:
T:expr(E)           3   A node of type T with a value that satisfies
                        the expression E
T:val(V)            3   A node of type T with a value that is equal to V
"""
import re
import numbers
import collections
import functools
import logging

from pprint import pprint

S_TYPE = lambda x, token: ('type', token)
S_IDENTIFIER = lambda x, token: ('identifier', token[1:])
S_QUOTED_IDENTIFIER = lambda x, token: S_IDENTIFIER(None,
                                                    token.replace('"', ''))
S_PCLASS = lambda x, token: ('pclass', token[1:])
S_PCLASS_FUNC = lambda x, token: ('pclass_func', token[1:])
S_NTH_FUNC = lambda x, token: ('nth_func', token[1:])
S_OPER = lambda x, token: ('operator', token)
S_EMPTY = lambda x, token:  ('empty', ' ')
S_UNK = lambda x, token: ('unknown', token)
S_INT = lambda x, token: ('int', int(token))
S_FLOAT = lambda x, token: ('float', float(token))
S_WORD = lambda x, token: ('word', token[1:-1])
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
    (ur"\"([_a-zA-Z]|[^\0-\0177]|\\[^\s0-9a-fA-F])([_a-zA-Z0-9\-]" \
     ur"|[^\u0000-\u0177]|(\\[^\s0-9a-fA-F]))*\"", S_WORD),
    (r'\.?\"([^"\\]|\\[^"])*\"', S_QUOTED_IDENTIFIER),
    (ur"\.([_a-zA-Z]|[^\0-\0177]|\\[^\s0-9a-fA-F])([_a-zA-Z0-9\-]" \
     ur"|[^\u0000-\u0177]|(\\[^\s0-9a-fA-F]))*", S_IDENTIFIER),
    (r":(root|empty|first-child|last-child|only-child)", S_PCLASS),
    (r":(has|expr|val|contains)", S_PCLASS_FUNC),
    (r":(nth-child|nth-last-child)", S_NTH_FUNC),
    (r"(&&|\|\||[\$\^<>!\*]=|[=+\-*/%<>])", S_BINOP),
    (r"true|false|null", S_VALS),
    (r"n", S_VAR),
    (r"odd|even", S_KEYWORD),
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
    'siblings'      # if parent is an array, number of elements in it
])


def object_iter(obj, parent=None, parent_key=None, idx=None,
                siblings=None):
    """Yields each node of object graph in postorder."""

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

    A simple top-down recursive-descendant parser of jsonselect selectors.
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
        elif not len(results):
            return None
        return results

    def selector_production(self, tokens):
        """Production for a full selector."""

        print tokens
        log.debug(tokens)
        validators = []
        # the following productions should return predicate functions.

        if self.peek(tokens, 'type'):
            type_ = self.match(tokens, 'type')
            validators.append(self.type_production(type_))

        if self.peek(tokens, 'identifier'):
            key = self.match(tokens, 'identifier')
            validators.append(self.key_production(key))

        if self.peek(tokens, 'pclass'):
            pclass = self.match(tokens, 'pclass')
            validators.append(self.pclass_production(pclass))

        if self.peek(tokens, 'nth_func'):
            nth_func = self.match(tokens, 'nth_func')
            validators.append(self.nth_child_production(nth_func, tokens))
        #self.pclass_func_production(pclass_func, tokens, validators)

        if self.peek(tokens, 'pclass_func'):
            pclass_func = self.match(tokens, 'pclass_func')
            validators.append(self.pclass_func_production(pclass_func, tokens))

        if not len(validators):
            raise SelectorSyntaxError('no selector recognized.')

        # apply validators from a selector expression to self.obj
        print 'validators: ', validators
        results = self._match_nodes(validators, self.obj)

        print tokens
        if self.peek(tokens, 'operator'):
            operator = self.match(tokens, 'operator')
            rvals = self.selector_production(tokens)
            if operator == ',':
                results.extend(rvals)
            elif operator == '>':
                results = self.parents(results, rvals)
            elif operator == '~':
                results = self.siblings(results, rvals)
            elif operator == ' ':
                results = self.ancestors(results, rvals)
            else:
                raise SelectorSyntaxError("unrecognized operator '%s'" \
                                          % operator)
        else:
            if len(tokens):
                print tokens
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
        elif pclass == 'empty':
            return lambda node: isinstance(node.value, list) and not len(node.value)
        else:
            raise SelectorSyntaxError("unrecognized pclass %s" % pclass)


    def pclass_func_production(self, pclass, tokens):
        args = self.parse_pclass_func_args(tokens)[1:-1]
        if pclass == 'has':
            # T:has(S)
            # A node of type T which has a child node satisfying the selector S
            for i, token in enumerate(args):
                if token[1] == '>':
                    args[i] = (token[0], ' ')
            rvals = self.selector_production(args)
            ancestors = [node.parent for node in rvals]
            return lambda node: node in ancestors

        if pclass == 'contains':
            return lambda node: isinstance(node.value, basestring) and \
                    node.value.find(args[0][1]) >= 0

        if pclass == 'val':
            return lambda node: isinstance(node.value, basestring) and \
                    node.value == args[0][1]

        if pclass == 'has':
            return lambda Node: False

        raise SelectorSyntaxError("unsupported pclass function %s" % pclass)

    def parse_pclass_func_args(self, tokens):
        """Parse arguments to a psuedoclass function.

        Raises SelectorSyntaxError if bad arguments found.

        TODO: trash this function (?)
        """
        expected = ['int', 'binop', 'float', 'var', 'val', 'keyword',
                    'operator', 'pclass', 'identifier']
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
            else:
                args.append(tokens.pop(0))
        else:
            raise SelectorSyntaxError('Ran out of tokens looking for ")"')

        if self.peek(tokens, 'operator') == ')':
            args.append(tokens.pop(0))
        else:
            raise SelectorSyntaxError()

        return args

    def nth_child_production(self, lexeme, tokens):
        """Parse args and pass them to pclass_func_validator."""

        args = self.parse_pclass_func_args(tokens)
        # TODO: compile this into a global
        x = ''.join([str(t[1]) for t in args])
        nth_pat = r"^\s*\(\s*(?:([+\-]?)([0-9]*)n\s*(?:([+\-])\s*([0-9]))?|(odd|even)|([+\-]?[0-9]+))\s*\)"
        pat = re.match(nth_pat, x)

        if pat.group(5):
            a = 2
            b = 1 if pat.group(5) == 'odd' else 0
        elif pat.group(6):
            a = 0
            b = int(pat.group(6))
        else:
            sign = pat.group(1) if pat.group(1) else '+'
            coef = pat.group(2) if pat.group(2) else '1' 
            a = eval(sign + coef)
            b = eval(pat.group(3) + pat.group(4)) if pat.group(3) else 0

        reverse = False
        if lexeme == 'nth-last-child':
            reverse = True

        def validate(node):
            """This crazy function taken from jsonselect.js:444."""

            if not node.siblings:
                return False

            idx = node.idx - 1
            tot = node.siblings

            if reverse:
                idx = tot - idx
            else:
                idx += 1

            if a == 0:
                m = b == idx
            else:
                mod = (idx - b) % a
                m = not mod and (idx * a + b) >= 0
            return m

        return validate

    def _match_nodes(self, validators, obj):
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

    log.info(selector)
    parser = Parser(obj)
    try:
        return parser.parse(lex(selector))
    except SelectorSyntaxError, e:
        log.exception(e)
        return False
