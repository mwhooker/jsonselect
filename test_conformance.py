#!/usr/bin/python

import functools
import os
import os.path
import logging
from jsonselect import select
from collections import defaultdict, namedtuple


log = logging.getLogger(__name__)

TestInputs = namedtuple('TestInputs', ['selector', 'input', 'output'])

def find_files(files):
    """
    Group directory listing into (selector, json, output) tuples.

    >>> hash(frozenset(find_files([
    ... 'sibling.json',
    ... 'sibling_childof.output',
    ... 'sibling_childof.selector',
    ... 'sibling_descendantof.output',
    ... 'sibling_descendantof.selector',
    ... 'foo.json',
    ... 'foo_bar.output',
    ... 'foo_bar.selector'
    ... ])))
    -765392879613439339
    """

    sorted_files = defaultdict(TestInputs)
    for file in files:
        root, ext = os.path.splitext(file)
        prefix = root.split('_')[0]
        setattr(sorted_files[], ext, 


    """
    return [
        ('sibling_childof.selector', 'sibling.json', 'sibling_childof.output'),
        ('sibling_descendantof.selector', 'sibling.json', 'sibling_descendantof.output'),
        ('foo_bar.selector', 'foo.json', 'foo_bar.output')
    ]
    """

def get_ctests(test_path):
    file_list = os.listdir(test_path)
    inputs = {}
    join_f = functools.partial(os.path.join, test_path)
    for files in find_files(file_list):
        (selector_path, input_path, output_path) = map(join_f, files)

        if input_path not in inputs:
            with open(input_path) as f:
                inputs[input_path] = f.readlines()

        with open(selector_path) as selector_f:
            with open(output_path) as output_f:
                yield (selector.readlines(),
                       inputs[input_path],
                       output_f.readlines())


if __name__ == '__main__':

    for level in ('level_1', 'level_2', 'level_3'):
        test_failures = []
        test_path = os.path.join('conformance_tests', level)
        log.info("Running tests in %s" % test_path)

        for (selector, input, output) in get_ctests(test_path):
            if select(selector, input) != output:
                test_failures.append(selector)

        if len(test_failures):
            log.info("%s failed" % level)
            for failure in test_failures:
                log.debug(failure)
