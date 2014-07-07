def load_tests(*args, **kwargs):
    """ Prevents DiscoverRunner from looking into this directory """
    from unittest.suite import TestSuite
    return TestSuite()
