import re
import numbers
import collections
import functools


S_TYPE = lambda x, token: ('type', token)
S_IDENTIFIER = lambda x, token: ('identifier', token[1:])
S_QUOTED_IDENTIFIER = lambda x, token: S_IDENTIFIER(None, token.replace('"', ''))
S_PCLASS = lambda x, token: ('pclass', token[1:])
S_PCLASS_FUNC = lambda x, token: ('pclass_func', token)
S_OPER = lambda x, token: ('operator', token)
S_EMPTY = lambda x, token:  ('empty', '')
S_UNK = lambda x, token: ('unknown', token)
S_INT = lambda x, token: ('int', int(token))
S_FLOAT = lambda x, token: ('float', float(token))
S_WORD = lambda x, token: ('word', token)
S_BINOP = lambda x, token: ('binop', token)
S_VALS = lambda x, token: ('val', token)

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
    (r"\w+", S_WORD),
])


def lex(selector):
    tokens, rest = SCANNER.scan(selector)
    if not len(tokens):
        if rest:
            raise Exception("leftover input: %s" % rest)
    return tokens

# parents is a list of node names along the path from the root to current node
Node = collections.namedtuple('Node', ['value', 'parents', 'sibling_idx',
                                       'siblings'])

def object_iter(obj, parents=[], siblings=None, sibling_idx=None):
    """
    return type: Node
    """

    if isinstance(obj, list):
        _siblings = len(obj)
        for i, elem in enumerate(obj):
            for node in object_iter(elem, parents, _siblings, i):
                yield node
    elif isinstance(obj, collections.Mapping):
        for key in obj:
            for node in object_iter(obj[key], parents + [key]):
                yield node
    yield Node(value=obj, parents=parents, siblings=siblings,
               sibling_idx=sibling_idx)


class Parser(object):

    def __init__(self, obj):
        self.obj = obj
        self.results = []

    def select(self, tokens):

        exprs = []

        while True:

            if self._peek(tokens, 'operator') == ',':
                self._match(tokens, 'operator')
                self.select(tokens)
                break

            expr = self._parse(tokens)
            if not expr:
                break
            exprs.append(expr)

        if tokens:
            print "leftover tokens: ", tokens

        for node in object_iter(self.obj):
            results = [expr(node) for expr in exprs]
            if all(results):
                self.results.append(node.value)


    def _parse(self, tokens):
        """
        Read from tokens until expression is found.
        Return function which takes a node as an argument and returns the
        result of the expression applied to the node.
        Modifies token stream.
        """


        if self._peek(tokens, 'type'):
            type_ = self._match(tokens, 'type')
            return functools.partial(self.select_type, type_)

        if self._peek(tokens, 'identifier'):
            id_ = self._match(tokens, 'identifier')
            return functools.partial(self.select_key, id_)

        if self._peek(tokens, 'pclass'):
            pclass = self._match(tokens, 'pclass')
            return functools.partial(self.select_pclass, pclass)

        if self._peek(tokens, 'operator') == '*':
            self._match(tokens, 'operator')
            return lambda x: True

        if self._peek(tokens, 'pclass_func'):
            pass


        return None

    def _match(self, tokens, ttype):
        if not self._peek(tokens, ttype):
            raise Exception('match not successful')

        t = tokens.pop(0)
        return t[1]

    def _peek(self, tokens, ttype):
        if not tokens:
            return False
        if tokens[0][0] == ttype:
            return tokens[0][1]
        else:
            return False

    @staticmethod
    def select_pclass(pclass, node):

        if pclass == 'first-child':
            if not node.siblings:
                return False
            return node.sibling_idx == 0
        elif pclass == 'last-child':
            if not node.siblings:
                return False
            return node.sibling_idx + 1 == node.siblings
        elif pclass == 'only-child':
            if not node.siblings:
                return False
            return node.siblings == 1
        elif pclass == 'root':
            return len(node.parents) == 0

    @staticmethod
    def select_pclass_function(pclass, args, node):
        pass


    @staticmethod
    def select_type(ttype, node):
        """

        >>> select_type('string', 'a')
        True
        >>> select_type('number', 1)
        True
        """

        assert ttype

        map = {
            'string': basestring,
            'number': numbers.Number,
            'object': collections.Mapping,
            'array': collections.Set,
            'boolean': bool,
            'null': type(None)
        }
        return isinstance(node.value, map[ttype])


    @staticmethod
    def select_key(lexeme, node):

        assert lexeme

        if len(node.parents):
            return node.parents[-1] == lexeme
        return False



def select(selector, obj):
    #if isinstance(obj, dict):
    #    obj = make_hashable(obj)
    parser = Parser(obj)
    parser.select(lex(selector))
    return parser.results



class EOFException(Exception):
    pass

class SyntaxError(Exception):
    def __init__(self, ext, input, line, column, peek):
        msg = "Syntax error on line %s column %s while processing '%s'" % (
            line, column, ext)
        msg += "\n peek = %s" % peek
        msg += "\n %s" % input
        super(SyntaxError, self).__init__(msg)

