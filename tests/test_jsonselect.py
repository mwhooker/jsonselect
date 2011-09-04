from unittest import TestCase
from jsonselect import jsonselect


class TestJsonselect(TestCase):

    def setUp(self):
        self.obj = {
            'hello': 'world',
            'foo': [1, 2, 3],
            'bar': {
                'x': 'y'
            }
        }
        self.parser = jsonselect.Parser(self.obj)

    def test_syntax_error_returns_false(self):
        self.assertFalse(jsonselect.select('gibberish', self.obj))

    def test_no_results_returns_none(self):
        self.assertEquals(jsonselect.select('.foobar', self.obj), None)
