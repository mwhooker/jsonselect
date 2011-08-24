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

        self.node_keywords = (
            'root',
            'nth-child',
            'nth-last-child',
            'first-child',
            'last-child',
            'only-child',
            'empty',
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
            if b in self.node_keywords:
                return (b, 'N')
            else:
                self._syntax_error(b)

        t = self.peek
        self.peek = ' '
        return (t, 'UNK')

    def _syntax_error(self, info):
        raise SyntaxError(info, self.input.getvalue(), self.line, self.column, self.peek)
            

def select(selector, input):
    print "select '%s'" % selector
    lexer = Lexer(selector)
    while True:
        try:
            print lexer.scan()
        except EOFException, e:
            return
        except SyntaxError, e:
            print e
            return



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

