import re

"""
from jsonselect.json

/^(?:([\r\n\t\]+)|([~*,>\)\(])|(string|boolean|null|array|object|number)|(:(?:root|first-child|last-child|only-child))|(:(?:nth-child|nth-last-child|has|expr|val|contains))|(:\w+)|(?:(\.)?(\"(?:[^\\\"]|\\[^\"])*\"))|(\")|\.((?:[_a-zA-Z]|[^\0-\0177]|\\[^\r\n\f0-9a-fA-F])(?:[_a-zA-Z0-9\-]|[^\u0000-\u0177]|(?:\\[^\r\n\f0-9a-fA-F]))*))/ 

        "^(?" +
        # (1) whitespace
        "([\r\n\t\ ]+)|" +
        # (2) one-char ops
        "([~*,>\)\(])|" +
        # (4) pseudo classes
        # (5) pseudo functions
        # (6) bogusly named pseudo something or others
        "(:\w+)|" +
        # (7 & 8) identifiers and JSON strings
        # (8) bogus JSON strings missing a trailing quote
        "(\\")|" +
        # (9) identifiers (unquoted)
        ")"
    );
"""

S_TYPE = lambda x, token: ('type', token)
S_IDENTIFIER = lambda x, token: ('identifier', token)
S_PCLASS = lambda x, token: ('pclass', token)
S_PCLASS_FUNC = lambda x, token: ('pclass_func', token)
S_OPER = lambda x, token: ('operator', token)
S_EMPTY = lambda x, token:  ('empty', '')
S_UNK = lambda x, token: ('unknown', token)
S_INT = lambda x, token: ('int', int(token))
S_WORD = lambda x, token: ('word', token)
S_BINOP = lambda x, token: ('binop', token)
S_VALS = lambda x, token: ('val', token)

SCANNER = re.Scanner([
    (r"([~*,>\)\(])", S_OPER),
    (r"\s", S_EMPTY),
    (r"(string|boolean|null|array|object|number)", S_TYPE),
    (r"""(?:(\.)?(\"(?:[^"]|\\[^"])*\"))""", S_IDENTIFIER),
    (u"\.((?:[_a-zA-Z]|[^\0-\0177]|\\[^\s0-9a-fA-F])(?:[_a-zA-Z0-9\-]" \
     u"|[^\u0000-\u0177]|(?:\\[^\s0-9a-fA-F]))*)", S_IDENTIFIER),
    (r"(:(root|first-child|last-child|only-child))", S_PCLASS),
    (r"(:(nth-child|nth-last-child|has|expr|val|contains))", S_PCLASS_FUNC),
    (r"(&&|\|\||[\$\^<>!\*]=|[=+\-*/%<>])", S_BINOP),
    (r"(true|false|null)", S_VALS),
    (r"(-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)", S_INT),
    (r"(\w+)", S_WORD),
])


def lex(selector):
    rest = selector
    while True:
        tokens, rest = SCANNER.scan(rest)
        if rest:
            print rest
        if not len(tokens):
            break
        yield tokens

def select(selector, obj):
    print selector
    for token in lex(selector):
        print 'TOKEN ', token



class EOFException(Exception):
    pass

class SyntaxError(Exception):
    def __init__(self, ext, input, line, column, peek):
        msg = "Syntax error on line %s column %s while processing '%s'" % (
            line, column, ext)
        msg += "\n peek = %s" % peek
        msg += "\n %s" % input
        super(SyntaxError, self).__init__(msg)

def nchild(idx, input):
    found = []

    def _find(input):
        if isinstance(input, dict):
            for key in input:
                _find(input[key])
        if isinstance(input, list):
            try:
                found.append(input[idx])
                _find(input[idx])
            except IndexError:
                pass
    _find(input)
    return found

def select_type(lexeme, input):
    """

    >>> select_type('string', ['a', 1, 'b'])
    ['a', 'b']
    >>> select_type('number', {'a': 1, 'b': {'c': 2}})
    [1, 2]
    """

    def _match(type_):
        map = {
            'string': str,
            'number': int,
            'object': dict,
            'array': list,
            'boolean': bool,
            'null': type(None)
        }
        def _do(val):
            if type_ == '*':
                return True
            return isinstance(val, map[type_])
        return _do

    found = []
    match = _match(lexeme)

    def _select(input):
        if isinstance(input, list):
            for elem in input:
                if match(elem):
                    found.append(elem)
        if isinstance(input, dict):
            for key in input:
                if match(input[key]):
                    found.append(input[key])
                _select(input[key])

    _select(input)

    return found

def select_key(lexeme, input):
    """

    >>> select_key('b', {'a': {'b': 1}})
    [1]
    >>> select_key('b',{'a': {'b': 1}, 'c': {'b': 2}})
    [1, 2]
    >>> select_key('b', {'a': {'b': {'c': 1}}})
    [{'c': 1}]
    >>> select_key('a', {'a': {'a': 1}})
    [1, {'a': 1}]
    """

    found = []
    def _search(target):
        if isinstance(target, dict):
            for key in target:
                if isinstance(target[key], dict):
                    _search(target[key])
                if key == lexeme:
                    found.append(target[key])
        elif isinstance(target, list):
            for elem in target:
                _search(elem)

    _search(input)
    return found
