from unittest import TestCase
from jsonselect import jsonselect


class TestPclassFuncArgs(TestCase):

    def setUp(self):
        self.parser = jsonselect.Parser({})

    def test_parse_pclass_func_args(self):
        should_pass = (
            '(1+2)',
            '(1 + (2 * 4))',
            '(-n+2)'
        )

        for input in should_pass:

            tokens = jsonselect.lex(input)
            cpy = list(tokens)
            self.assertEqual(
                self.parser.parse_pclass_func_args(tokens),
                cpy,
                input
            )
            self.assertFalse(len(tokens))

        tokens = jsonselect.lex('(n+2), object')
        self.assertEqual(
            self.parser.parse_pclass_func_args(tokens),
            [('operator', '('), ('var', 'n'), ('binop', '+'), ('int', 2), ('operator', ')')]
        )
        self.assertEqual(
            tokens,
            [('operator', ','), ('type', 'object')]
        )

        tokens = jsonselect.lex('(import sys; sys.exit(0))')
        self.assertRaises(jsonselect.SelectorSyntaxError,
                          self.parser.parse_pclass_func_args, tokens)

        tokens = jsonselect.lex('(1 + ( 2 - 3)')
        self.assertRaises(jsonselect.SelectorSyntaxError,
                          self.parser.parse_pclass_func_args, tokens)


    def test_eval_args(self):
        tokens = jsonselect.lex('(1 + 2)')
        self.assertTrue(3, self.parser.eval_args(tokens, n=3))
