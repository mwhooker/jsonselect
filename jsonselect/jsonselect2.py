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
        self._validators = []

    @property
    def results(self):
        # single results should be returned as a primitive
        if len(self._results) == 1:
            return self._results[0]
        return self._results

    def add_found_node(self, node):
        self._results.append(node.value)

    def validate(self, validators, node):
        return all([validate(node) for validate in validators])

    def eval(self, validators, obj):
        for node in object_iter(obj):
            if self.validate(validators, node):
                self.add_found_node(node)

    def select(self, tokens):
        self.parse(tokens)
        self.eval(self._validators, self.obj)

    def parse(tokens):

        if self._peek(tokens, 'type'):
            type_ = self._match(tokens, 'type')
            self.type_production(type_)

        if self._peek(tokens, 'identifier'):
            key = self._match(tokens, 'identifier')
            self.key_production(key)

        if self._peek(tokens, 'pclass'):
            pclass = self._match(tokens, 'pclass')
            self.pclass_production(pclass)

        if self._peek(tokens, 'operator') == '*':
            self._match(tokens, 'operator')
            self._validators.append(lambda x: True)

        """
        if self._peek(tokens, 'pclass_func'):
            pclass_func = self._match(tokens, 'pclass_func')
            return self.pclass_func_production(pclass_func, tokens)
        """


    @staticmethod
    def type_production(type_):
        assert ttype

        map = {
            'string': basestring,
            'number': numbers.Number,
            'object': collections.Mapping,
            'array': list,
            'boolean': bool,
            'null': type(None)
        }
        self._validators.append(lambda node: isinstance(node.value, map[ttype]))


    @staticmethod
    def key_production(key):
        assert key

        def validate(node):
            if len(node.parents):
                return node.parents[-1] == lexeme
            return False
        self._validators.append(key_production)


    @staticmethod
    def pclass_production(pclass):

        if pclass == 'first-child':
            def _validate(node):
                if not node.siblings:
                    return False
                return node.sibling_idx == 1
            self._validators.append(_validate)
        elif pclass == 'last-child':
            def _validate(node):
                if not node.siblings:
                    return False
                return node.sibling_idx == node.siblings
            self._validators.append(_validate)
        elif pclass == 'only-child':
            def _validate(node):
                if not node.siblings:
                    return False
                return node.siblings == 1
            self._validators.append(_validate)
        elif pclass == 'root':
            self._validators.append(lambda node: len(node.parents) == 0)
        else:
            raise Exception("unrecognized pclass %s" % pclass)


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
To merge:
    _expr_production
    pclass_func_production
    _parse
    eval
    _rename_1
"""
