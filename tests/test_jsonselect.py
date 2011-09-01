from unittest import TestCase
from jsonselect import jsonselect


class TestPclassFuncArgs(TestCase):
    def setUp(self):
        self.parser = jsonselect.Parser({})

    def test_parse_pclass_func_args(self):
        tokens = jsonselect.lex('(1+2)')
        self.parser.parse_pclass_func_args(tokens)

        tokens = jsonselect.lex('(1 + (2 * 4))')
        self.parser.parse_pclass_func_args(tokens)

        tokens = jsonselect.lex('(-n+2)')
        self.parser.parse_pclass_func_args(tokens)

        tokens = jsonselect.lex('(import sys; sys.exit(0))')
        self.assertRaises(jsonselect.SelectorSyntaxError,
                          self.parser.parse_pclass_func_args, tokens)

        tokens = jsonselect.lex('(1 + ( 2 - 3)')
        self.assertRaises(jsonselect.SelectorSyntaxError,
                          self.parser.parse_pclass_func_args, tokens)


    def test_eval_args(self):
        tokens = jsonselect.lex('(1 + 2)')
        self.assertEqual(3, self.parser.eval_args(tokens))

        tokens = jsonselect.lex('(-n+2)')
        self.assertEqual(1, self.parser.eval_args(tokens, 1))
