#!/usr/bin/env python

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_project.settings'
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'test_project'))

import django
if django.VERSION >= (1, 6):
    from django.test.runner import DiscoverRunner as Runner
else:
    from django.test.simple import DjangoTestSuiteRunner as Runner

def runtests():
    try:
        django.setup()
    except AttributeError:
        pass
    runner = Runner(
        pattern='*.py',
        interactive=False,
        failfast=False,
    )
    failed = runner.run_tests(('tests',))
    return (failed == 0)

if __name__ == '__main__':
    sys.exit(0 if runtests() else 1)

