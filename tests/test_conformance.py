import glob
import os
import os.path
import json
import collections
from jsonselect import jsonselect
from unittest import TestCase
import logging


log = logging.getLogger(__name__)

class TestConformance(TestCase):
    pass

def get_ctests(test_path):
    inputs = {}
    for selector_path in glob.iglob(os.path.join(test_path, '*.selector')):
        selector_file = os.path.basename(selector_path)
        root, ext = os.path.splitext(selector_file)
        prefix = root.split('_')[0]

        input_file = "%s%sjson" % (prefix, os.extsep)
        input_path = os.path.join(test_path, input_file)
        output_file = "%s%soutput" % (root, os.extsep)
        output_path = os.path.join(test_path, output_file)

        if input_path not in inputs:
            with open(input_path) as f:
                inputs[input_path] = json.load(f)

        with open(selector_path) as selector_f:
            with open(output_path) as output_f:
                yield (selector_f.read().strip(),
                       inputs[input_path],
                       read_output(output_f))


def read_output(output_f):
    output = output_f.read().strip()
    try:
        output = json.loads(output)
        return output
    except ValueError, e:
        output_f.seek(0)
        marker_map = {
            '{': '}',
            '[': ']'
        }
        output = []
        collected = ''
        marker = None
        for line in output_f:

            # int value?
            try:
                output.append(int(line))
                continue
            except ValueError:
                pass

            # string
            if line[0] == '"':
                output.append(json.loads(line))
                continue

            # closing object or array
            if line[0] == marker:
                collected += line
                output.append(json.loads(collected))
                collected = ''
                marker = None
                continue

            # opening object or array
            if line[0] in '[{':
                marker = marker_map[line[0]]
                collected += line
                continue

            # object or array body
            if marker:
                collected += line
                continue

            # anything else
            output.append(line)

        return output


def create_ctest(selector, input, output):
    def _test(self):
        parser = jsonselect.Parser(input)
        tokens = jsonselect.lex(selector)

        try:
            if output[0][:5] == 'Error':
                self.assertRaises(
                    jsonselect.SelectorSyntaxError,
                    parser.parse,
                    (tokens,)
                )
                return
        except (IndexError, TypeError, KeyError):
            pass

        selection = parser.parse(tokens)

        msg = "%s" % selector
        msg += "\n%s\n!=\n%s" % (selection, output)
        log.debug('creating %s("%s")' % (_test.__name__, selector))

        self.assertEqual(
            normalize(selection),
            normalize(output),
            msg=msg
        )
    return _test

def normalize(obj):
    if isinstance(obj, list):
        obj = sorted(obj)
    return obj

def add_ctests(test_path, name):
    for i, inputs in enumerate(get_ctests(test_path)):
        new_test = create_ctest(*inputs)
        new_test.__name__ = 'test_%s_%s' % (i, name)
        setattr(TestConformance, new_test.__name__, new_test)

for level in ('level_%s' % level for level in [1, 2, 3]):
    test_path = os.path.join('conformance_tests', 'upstream', level)

    add_ctests(test_path, level)

add_ctests(os.path.join('conformance_tests', 'custom'), 'custom')
