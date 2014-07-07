#!/usr/bin/env python

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.project.settings'
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'tests', 'project'))

import django
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment, teardown_test_environment

def runtests():
    try:
        django.setup()
    except AttributeError:
        pass
    runner = DiscoverRunner(
        pattern='*.py',
        interactive=False,
        failfast=False,
    )
    failed = runner.run_tests(('tests',))
    return (failed == 0)

if __name__ == '__main__':
    sys.exit(0 if runtests() else 1)

