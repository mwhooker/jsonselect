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
S_EMPTY = lambda x, token:  ('empty', True)
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
# sibling_idx is 1 indexed
Node = collections.namedtuple('Node', ['value', 'parents', 'sibling_idx',
                                       'siblings'])

def object_iter(obj, parents=[], sibling_idx=None, siblings=None):
    """
    Yields each node of object graph in postorder
    """

    if isinstance(obj, list):
        _siblings = len(obj)
        for i, elem in enumerate(obj):
            for node in object_iter(elem, parents, i+1, _siblings):
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
        self._results = []

    @property
    def results(self):
        # single results should be returned as a primitive
        if len(self._results) == 1:
            return self._results[0]
        return self._results

    def add_found_node(self, node):
        self._results.append(node.value)

    def select(self, tokens):

        exprs = []

        while True:

            if self._peek(tokens, 'operator') == ',':
                self._match(tokens, 'operator')
                self.select(tokens)
                break
            
            """
            if self._peek(tokens, 'empty'):
                self._match(tokens, 'empty')
                continue
            """

            expr = self._parse(tokens)
            if not expr:
                break
            exprs.append(expr)

        if tokens:
            print "leftover tokens: ", tokens

        for node in object_iter(self.obj):
            results = [expr(node) for expr in exprs]
            print node
            print results
            if all(results):
                self.add_found_node(node)


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
            pclass_func = self._match(tokens, 'pclass_func')
            return self._parse_pclass_func(pclass_func, tokens)


        return None

    def _parse_pclass_func(self, lexeme, tokens):
        """
        Parse args and parse them to select_pclass_function.
        """
        if self._peek(tokens, 'operator') == '(':
            self._match(tokens, 'operator')
            args = []

            while tokens:
                if self._peek(tokens, 'operator') == ')':
                    self._match(tokens, 'operator')
                    break
                args.append(tokens.pop(0))
            else:
                raise Exception('syntax error')

            return functools.partial(self.select_pclass_function, lexeme, args)
        else:
            raise Exception('syntax error')

    def select_pclass_function(self, pclass, args, node):
        args = list(args)
        if pclass == 'nth-child':
            if not node.siblings:
                return False
            if self._peek(args, 'word') == 'odd':
                self._match(args, 'word')
                return node.sibling_idx % 2 == 1
            elif self._peek(args, 'word') == 'even':
                return node.sibling_idx % 2 == 0
            elif self._peek(args, 'int'):
                idx = self._match(args, 'int')
                return node.sibling_idx == idx
            else:
                raise Exception('syntax error')
        elif pclass == 'nth-last-child':
            return False
        else:
            raise Exception('syntax error')

    @staticmethod
    def select_pclass(pclass, node):

        if pclass == 'first-child':
            if not node.siblings:
                return False
            return node.sibling_idx == 1
        elif pclass == 'last-child':
            if not node.siblings:
                return False
            return node.sibling_idx == node.siblings
        elif pclass == 'only-child':
            if not node.siblings:
                return False
            return node.siblings == 1
        elif pclass == 'root':
            return len(node.parents) == 0


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
            'array': list,
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

def select(selector, obj):
    parser = Parser(obj)
    parser.select(lex(selector))
    return parser.results


"""
class SyntaxError(Exception):
    def __init__(self, ext, input, line, column, peek):
        msg = "Syntax error on line %s column %s while processing '%s'" % (
            line, column, ext)
        msg += "\n peek = %s" % peek
        msg += "\n %s" % input
        super(SyntaxError, self).__init__(msg)
"""
