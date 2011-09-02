import glob
import os
import os.path
import json
import collections
from jsonselect import select
from unittest import TestCase


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
    except ValueError, e:
        output = output.replace('"','').split()
        for i, line in enumerate(output):
            try:
                output[i] = int(line)
            except ValueError:
                pass
    return output

def create_test(selector, input, output):
    def _test(self):
        selection = select(selector, input)

        msg = "%s" % selector
        msg += "\n%s\n!=\n%s" % (selection, output)

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

def add_tests(test_path, name):
    for i, inputs in enumerate(get_ctests(test_path)):
        new_test = create_test(*inputs)
        new_test.__name__ = 'test_%s_%s' % (i, name)
        setattr(TestConformance, new_test.__name__, new_test)

for level in ('level_%s' % level for level in [1, 2, 3]):
    test_path = os.path.join('conformance_tests', 'upstream', level)

    add_tests(test_path, level)

add_tests(os.path.join('conformance_tests', 'custom'), 'custom')
