import StringIO
import re
ATOM_PATTERN = re.compile("[a-zA-Z0-9-]")


class EOFException(Exception):
    pass

class SyntaxError(Exception):
    def __init__(self, ext, input, line, column, peek):
        msg = "Syntax error on line %s column %s while processing '%s'" % (
            line, column, ext)
        msg += "\n peek = %s" % peek
        msg += "\n %s" % input
        super(SyntaxError, self).__init__(msg)

class Lexer(object):
    def __init__(self, input):
        self.eof = False
        self.column = 0
        self.line = 1
        self.peek = ' '
        self.input = StringIO.StringIO(input)
        self.types = (
            'string',
            'number',
            'object',
            'array',
            'boolean',
            'null'
        )

        self.pseudo_classes = (
            'root',
            'first-child',
            'last-child',
            'only-child',
            'empty'
        )
        self.pseudo_class_functions = (
            'nth-child',
            'nth-last-child',
            'has',
            'expr',
            'val',
            'contains'
        )

    def rewind(self):
        self.column -= 2
        self.input.seek(self.input.tell() - 2)
        return self.next()

    def next(self):
        self.peek = self.input.read(1)
        if not self.peek:
            self.eof = True
        """
        # if we uncomment this, we never get a chance to deal with what's on the
        # buffer
        if not self.peek:
            raise EOFException()
        """
        self.column += 1
        return self.peek

    def scan(self):
        if self.eof:
            raise EOFException
        while True:
            self.next()
            if not self.peek:
               break
            if self.peek in (' ', '\t'):
                continue
            elif self.peek == '\n':
                self.line += 1
            else:
                break


        if self.peek == '*':
            self.next()
            return ('*', 'T')


        if self.peek.isalpha():
            b = ''
            while self.peek.isalnum():
                b += self.peek
                self.next()

            self.rewind()
            if b in self.types:
                return (b, 'T')
            else:
                self._syntax_error(b)

        if self.peek == '.':
            b = ''
            self.next()
            if self.peek == '"':
                self.next()
                while True:
                    b += self.peek
                    self.next()
                    if self.peek == '"':
                        self.next()
                        break
            else:
                while self.peek.isalnum():
                    b += self.peek
                    self.next()
            self.rewind()
            return (b, 'KEY')

        if self.peek == ':':
            b = ''
            self.next()
            while self.peek:
                if not ATOM_PATTERN.match(self.peek):
                    break
                b += self.peek
                self.next()
            self.rewind()
            if b in self.pseudo_classes:
                return (b, 'P')
            elif b in self.pseudo_class_functions:
                return (b, 'PF')
            else:
                self._syntax_error(b)

        t = self.peek
        self.peek = ' '
        return (t, 'UNK')

    def _syntax_error(self, info):
        raise SyntaxError(info, self.input.getvalue(), self.line, self.column, self.peek)


def select(selector, input):
    print "select '%s'" % selector

    """
    if not isinstance(input, dict):
        raise Exception('expecting dict type')
    """


    lexer = Lexer(selector)

    while True:
        try:
            lexeme, token_type = lexer.scan()
        except EOFException, e:
            break
        except SyntaxError, e:
            print e
            return

        print "<%s, %s>" % (token_type, lexeme)
        if token_type == 'KEY':
            input = select_key(lexeme, input)

        if token_type == 'T':
            input = select_type(lexeme, input)

        if token_type == 'N':
            input = select_declaration(lexeme, input)

        if token_type == 'NARGS':
            pass

    return input

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

def select_declaration(lexeme, input):
    """
            'root',
            'first-child',
            'last-child',
            'only-child',
            'empty',
    """
    if lexeme == 'root':
        return input
    if lexeme == 'first-child':
        return nchild(0, input)
    if lexeme == 'last-child':
        return nchild(-1, input)
    """
    if lexeme == 'only-child':
        return hasnchildren(1, input)
    if lexeme == 'empty':
        return hasnchildren(0, input)
    """




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


"""
def lex(input):
    word = ''

    for char in input:
        if ATOM_PATTERN.match(char):
            word = word + char
        else:
            if len(word):
                yield word
                word = ''
            yield char
    if word:
        yield word
"""

class Interpreter(object):

    def __init__(self, input):
        self.input = input
        self.idx = 0

    @property
    def lookahead(self):
        try:
            val = self.input(self.idx)
        except IndexError:
            return None
        return val

    def match(self, terminal):
        if self.lookahead == terminal:
            self.idx += 1
        else:
            raise SyntaxError(terminal, self.input, idx, 0)

