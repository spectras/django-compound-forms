from django.test import TestCase as DjangoTestCase

class TestCase(DjangoTestCase):
    def assertCountEqual(self, *args, **kwargs):
        if hasattr(super(TestCase, self), 'assertCountEqual'):
            return super(TestCase, self).assertCountEqual(*args, **kwargs)
        else:
            return super(TestCase, self).assertItemsEqual(*args, **kwargs)
