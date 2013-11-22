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
"""
from __future__ import division
import re
import numbers
import collections
import logging
import json


log = logging.getLogger(__name__)

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
S_FLOAT = lambda x, token: ('float', float(token))
S_WORD = lambda x, token: ('word', token[1:-1])
S_BINOP = lambda x, token: ('binop', token)
S_VALS = lambda x, token: ('val', token)
S_KEYWORD = lambda x, token: ('keyword', token)
S_PVAR = lambda x, token: ('pvar', token)
S_EXPR = lambda x, token: ('expr', token)
S_NUMBER = lambda x, token: ('number', token)
S_STRING = lambda x, token: ('string', token)
S_PAREN = lambda x, token: ('paren', token)

SCANNER = re.Scanner([
    (r"\([^\)]+\)", S_EXPR),
    (r"[~*,>]", S_OPER),
    (r"\s", S_EMPTY),
    (r"(-?\d+(\.\d*)([eE][+\-]?\d+)?)", S_FLOAT),
    (r"string|boolean|null|array|object|number", S_TYPE),
    (ur"\"([_a-zA-Z]|[^\0-\0177]|\\[^\s0-9a-fA-F])([_a-zA-Z0-9\-]"
     ur"|[^\u0000-\u0177]|(\\[^\s0-9a-fA-F]))*\"", S_WORD),
    (r'\.?\"([^"\\]|\\[^"])*\"', S_QUOTED_IDENTIFIER),
    (ur"\.([_a-zA-Z]|[^\0-\0177]|\\[^\s0-9a-fA-F])([_a-zA-Z0-9\-]"
     ur"|[^\u0000-\u0177]|(\\[^\s0-9a-fA-F]))*", S_IDENTIFIER),
    (r":(root|empty|first-child|last-child|only-child)", S_PCLASS),
    (r":(has|expr|val|contains)", S_PCLASS_FUNC),
    (r":(nth-child|nth-last-child)", S_NTH_FUNC),
    (r"(&&|\|\||[\$\^<>!\*]=|[=+\-*/%<>])", S_BINOP),
    (r"true|false|null", S_VALS),
    (r"n", S_PVAR),
    (r"odd|even", S_KEYWORD),
])


EXPR_SCANNER = re.Scanner([
    (r"\s", S_EMPTY),
    (r"true|false|null", S_VALS),
    (r"-?\d+(\.\d*)?([eE][+\-]?\d+)?", S_NUMBER),
    (r"\"([^\]|\[^\"])*\"", S_STRING),
    (r"x", S_PVAR),
    (r"(&&|\|\||[\$\^<>!\*]=|[=+\-*/%<>])", S_BINOP),
    (r"\(|\)", S_PAREN)
])

class SelectorSyntaxError(Exception):
    pass

class LexingError(SelectorSyntaxError):
    pass

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

def lex(input, scanner=SCANNER):
    tokens, rest = scanner.scan(input)
    if not len(tokens):
        raise LexingError("no input parsed.")
    if len(rest):
        raise LexingError("found leftover tokens: (%s, %s)" % (tokens, rest))
    return [tok for tok in tokens if tok[0] != 'empty']

def lex_expr(expression):
    tokens = lex(expression, scanner=EXPR_SCANNER)
    for i, token in enumerate(tokens):
        if token[0] in ('number', 'string', 'val'):
            tokens[i] = (token[0], json.loads(tokens[i][1]))
    return tokens


class Parser(object):

    """
    Parse jsonselect queries.

    A simple top-down recursive-descendant parser of jsonselect selectors.
    Initialize with the object you wish to match against.

    Clients should only need to call Parser.parse, which accepts
    a list of tokens as generated by jsonselect.lex
    """

    nth_child_pat = re.compile(
        r"^\s*\(\s*(?:([+\-]?)([0-9]*)n\s*(?:([+\-])\s*([0-9]))?"
        r"|(odd|even)|([+\-]?[0-9]+))\s*\)"
    )

    def __init__(self, obj):
        """Create a parser for a particular object."""
        self.obj = obj

    def parse(self, selector):
        """Accept a list of tokens. Returns matched nodes of self.obj."""
        log.debug(self.obj)
        tokens = lex(selector)

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

        if self.peek(tokens, 'pclass_func'):
            pclass_func = self.match(tokens, 'pclass_func')
            validators.append(self.pclass_func_production(pclass_func, tokens))

        if not len(validators):
            raise SelectorSyntaxError('no selector recognized.')

        # apply validators from a selector expression to self.obj
        results = self._match_nodes(validators, self.obj)

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
                raise SelectorSyntaxError("unrecognized operator '%s'"
                                          % operator)
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
        pclass_map = {
            'first-child': lambda node: node.idx == 1,
            'last-child': lambda node: (node.siblings and
                                        node.idx == node.siblings),
            'only-child': lambda node: node.siblings == 1,
            'root': lambda node: not node.parent,
            'empty': lambda node: (isinstance(node.value, list) and
                                   not len(node.value))
        }

        try:
            return pclass_map[pclass]
        except KeyError:
            raise SelectorSyntaxError("unrecognized pclass %s" % pclass)

    def parse_expr(self, tokens, node):
        def types_eq(type_, *args):
            return all([isinstance(arg, type_) for arg in args])

        cmpf_map = {
            '*': lambda lhs, rhs: (types_eq(numbers.Number, lhs, rhs) and
                                   lhs * rhs),
            '/': lambda lhs, rhs: (types_eq(numbers.Number, lhs, rhs) and
                                   lhs / rhs),
            '%': lambda lhs, rhs: (types_eq(numbers.Number, lhs, rhs) and
                                   lhs % rhs),
            '+': lambda lhs, rhs: (types_eq(numbers.Number, lhs, rhs) and
                                   lhs + rhs),
            '-': lambda lhs, rhs: (types_eq(numbers.Number, lhs, rhs) and
                                   lhs - rhs),
            '<=': lambda lhs, rhs: (types_eq(numbers.Number, lhs, rhs) and
                                    lhs <= rhs),
            '<': lambda lhs, rhs: (types_eq(basestring, lhs, rhs) and
                                   lhs < rhs),
            '>=': lambda lhs, rhs: (types_eq(numbers.Number, lhs, rhs) and
                                    lhs >= rhs),
            '>': lambda lhs, rhs: (types_eq(basestring, lhs, rhs) and
                                   lhs > rhs),
            '$=': lambda lhs, rhs: (types_eq(basestring, lhs, rhs) and
                                    lhs.rfind(rhs) == len(lhs) - len(rhs)),
            '^=': lambda lhs, rhs: (types_eq(basestring, lhs, rhs) and
                                    lhs.find(rhs) == 0),
            '*=': lambda lhs, rhs: (types_eq(basestring, lhs, rhs) and
                                    lhs.find(rhs) != 0),
            '=': lambda lhs, rhs: lhs == rhs,
            '!=': lambda lhs, rhs: lhs != rhs,
            '&&': lambda lhs, rhs: lhs and rhs,
            '||': lambda lhs, rhs: lhs or rhs
        }

# ((12 % 10) + 40 = x)

        def parse(tokens):
            if not len(tokens):
                raise Exception

            if self.peek(tokens, 'paren') == '(':
                self.match(tokens, 'paren')
                lhs = parse(tokens)
                return lhs
            elif self.peek(tokens, 'pvar') is not None:
                self.match(tokens, 'pvar')
                lhs = node.value
            else:
                for tok in ('string', 'val', 'number'):
                    if self.peek(tokens, tok) is not None:
                        lhs = self.match(tokens, tok)
                        break

            if self.peek(tokens, 'paren') == ')':
                self.match(tokens, 'paren')
                return lhs

            op = self.match(tokens, 'binop')
            cf = cmpf_map[op]
            rhs = parse(tokens)

            return cf(lhs, rhs)

        return parse(tokens)

    def expr_production(self, args):
        tokens = lex_expr(args)
        return lambda node: self.parse_expr(list(tokens), node)

    def pclass_func_production(self, pclass, tokens):
        args = self.match(tokens, 'expr')

        if pclass == 'expr':
            return self.expr_production(args)

        args = lex(args[1:-1])

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
            return lambda node: (isinstance(node.value, basestring) and
                                 node.value.find(args[0][1]) >= 0)

        if pclass == 'val':
            return lambda node: (isinstance(node.value, basestring) and
                                 node.value == args[0][1])

        raise SelectorSyntaxError("unsupported pclass function %s" % pclass)

    def nth_child_production(self, lexeme, tokens):
        """Parse args and pass them to pclass_func_validator."""

        args = self.match(tokens, 'expr')

        pat = self.nth_child_pat.match(args)

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
        if Parser.peek(tokens, type_) is None:
            raise Exception('match not successful (%s, %s)' % (type_, tokens))

        token = tokens.pop(0)
        return token[1]

    @staticmethod
    def peek(tokens, type_):
        if not tokens:
            return None

        if isinstance(type_, list) and tokens[0][0] in type_:
            return tokens[0][1]
        elif tokens[0][0] == type_:
            return tokens[0][1]
        else:
            return None


def select(selector, obj):
    """Appy selector to obj and return matching nodes.

    If only one node is found, return it, otherwise return a list of matches.
    Returns False on syntax error. None if no results found.
    """

    parser = Parser(obj)
    try:
        return parser.parse(selector)
    except SelectorSyntaxError, e:
        log.exception(e)
        return False
