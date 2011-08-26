import re
import numbers
import collections


class hashabledict(dict, collections.Mapping):
    def __key(self):
        return tuple((k,self[k]) for k in sorted(self))
    def __hash__(self):
        return hash(self.__key())
    def __eq__(self, other):
        return self.__key() == other.__key()
    def __repr__(self):
        return "hashable(%s)" % super(hashabledict, self).__repr__()

def make_hashable(obj):
    if isinstance(obj, dict):
        for key in obj:
            obj[key] = make_hashable(obj[key])
        return hashabledict(obj)
    elif isinstance(obj, list):
        for i, elem in enumerate(obj):
            obj[i] = make_hashable(obj[i])
        return frozenset(obj)
    else:
        return obj




S_TYPE = lambda x, token: ('type', token)
S_IDENTIFIER = lambda x, token: ('identifier', token[1:])
S_QUOTED_IDENTIFIER = lambda x, token: S_IDENTIFIER(None, token.replace('"', ''))
S_PCLASS = lambda x, token: ('pclass', token)
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

def match(tokens, ttype):
    if not peek(tokens, ttype):
        raise Exception('match not successful')

    t = tokens.pop(0)
    return t[1]

def peek(tokens, ttype):
    if not tokens:
        return False
    if tokens[0][0] == ttype:
        return tokens[0][1]
    else:
        return False


def parse(tokens, obj):

    if peek(tokens, 'operator') == '*':
        return obj
    results = set([])
    print tokens

    if peek(tokens, 'type'):
        print tokens
        type_ = match(tokens, 'type')
        res = select_type(type_, obj)
        results.update(set(res))
        print 'type: ', res

    if peek(tokens, 'identifier'):
        print tokens
        id_ = match(tokens, 'identifier')
        res = select_key(id_, obj)
        print 'res: ', res
        results.intersection_update(set(res))
        print 'id: ', results

    if peek(tokens, 'operator') == ',':
        match(tokens, 'operator')
        results.update(parse(tokens, obj))
        print 'merged: ', results


    return results



def select(selector, obj):
    print selector
    print obj
    if isinstance(obj, dict):
        obj = make_hashable(obj)
    print 'after: ', obj
    return parse(lex(selector), obj)



def nchild(idx, input):
    found = []

    def _find(input):
        if isinstance(input, collections.Mapping):
            for key in input:
                _find(input[key])
        if isinstance(input, collections.Set):
            try:
                found.append(input[idx])
                _find(input[idx])
            except IndexError:
                pass
    _find(input)
    return found

def select_type(ttype, input):
    """

    >>> select_type('string', ['a', 1, 'b'])
    ['a', 'b']
    >>> select_type('number', {'a': 1, 'b': {'c': 2}})
    [1, 2]
    """

    if not ttype:
        return input

    def match(val):
        map = {
            'string': basestring,
            'number': numbers.Number,
            'object': collections.Mapping,
            'array': collections.Set,
            'boolean': bool,
            'null': type(None)
        }
        return isinstance(val, map[ttype])

    found = []

    def _select(input):
        if isinstance(input, collections.Set):
            for elem in input:
                _select(elem)
        if isinstance(input, collections.Mapping):
            for key in input:
                _select(input[key])
        if match(input):
            found.append(input)

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

    if not lexeme:
        return input

    found = []
    def _search(target):
        if isinstance(target, collections.Mapping):
            for key in target:
                _search(target[key])
                if key == lexeme:
                    found.append(target[key])
        elif isinstance(target, collections.Set):
            for elem in target:
                _search(elem)

    _search(input)
    return found


class EOFException(Exception):
    pass

class SyntaxError(Exception):
    def __init__(self, ext, input, line, column, peek):
        msg = "Syntax error on line %s column %s while processing '%s'" % (
            line, column, ext)
        msg += "\n peek = %s" % peek
        msg += "\n %s" % input
        super(SyntaxError, self).__init__(msg)

