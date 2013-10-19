from unittest import TestCase
from jsonselect import jsonselect


class TestPclassFuncArgs(TestCase):

    def setUp(self):
        self.parser = jsonselect.Parser({})

    def test_lex_expr(self):

        tokens = jsonselect.lex('(n+2), object')
        self.assertEqual(
            tokens,
            [('expr', '(n+2)'), ('operator', ','), ('type', 'object')]
        )

        self.assertRaises(jsonselect.LexingError,
                          jsonselect.lex, '(import sys; sys.exit(0))')

    def test_eval_args(self):
        self.assertEquals(self.parser.expr_production("(1 + 2)")(None), 3)
