from django.forms import CharField
from django.test import TestCase
from collections import OrderedDict
from compound_forms.forms import (MergingProxyForm, MergingCompoundModelForm,
                                  compoundform_factory)

from app.models import Normal, Other
from app.forms import NormalForm, OtherForm
from .data import NORMAL, OTHER
from .fixtures import NormalFixture, OtherFixture
from .formdata import FormData


class BasicProxyFormTest(NormalFixture, OtherFixture, TestCase):
    normal_count = 1
    other_count = 1

    """ Proxy forms act as proxy towards already existing forms """
    def _get_form(self, normal, other, **kwargs):
        ''' Helper function to build the form '''
        defaults = {
            'forms': OrderedDict((('normal', normal), ('other', other),)),
        }
        defaults.update(kwargs)
        return MergingProxyForm(**defaults)

    def test_basic_proxy_create(self):
        form = self._get_form(NormalForm(), OtherForm())
        # Test the forms are set on the proxy form, and regular form interface works
        self.assertEqual(tuple(form.forms.keys()), ('normal', 'other'))
        self.assertCountEqual(form.fields,
                              ('normal.common', 'normal.field_a',
                               'other.common', 'other.field_a'))
        self.assertCountEqual((field.name for field in form),
                              ('common', 'field_a',
                               'common', 'field_a'))

        # Test the field are actually the same
        self.assertIs(form.fields['normal.common'], form.forms['normal'].fields['common'])
        self.assertIs(form.fields['normal.field_a'], form.forms['normal'].fields['field_a'])
        self.assertIs(form.fields['other.common'], form.forms['other'].fields['common'])
        self.assertIs(form.fields['other.field_a'], form.forms['other'].fields['field_a'])

    def test_basic_proxy_initial(self):
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[1])
        form = self._get_form(NormalForm(instance=normal, prefix='normal'),
                              OtherForm(instance=other, prefix='other'))

        self.assertEqual(form['normal.common'].value(), NORMAL[1].common)
        self.assertEqual(form['normal.field_a'].value(), NORMAL[1].field_a)
        self.assertEqual(form['other.common'].value(), OTHER[1].common)
        self.assertEqual(form['other.field_a'].value(), OTHER[1].field_a)
        self.assertEqual(form.forms['normal']['common'].value(), NORMAL[1].common)
        self.assertEqual(form.forms['normal']['field_a'].value(), NORMAL[1].field_a)
        self.assertEqual(form.forms['other']['common'].value(), OTHER[1].common)
        self.assertEqual(form.forms['other']['field_a'].value(), OTHER[1].field_a)

    def test_basic_proxy_validate_correct(self):
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[1])
        form = self._get_form(NormalForm(instance=normal, prefix='normal'),
                              OtherForm(instance=other, prefix='other'))

        # Get and alter html form data
        data = FormData(form)
        data.set_form_field(form, 'normal.common', 'updated_nc')
        data.set_form_field(form, 'other.field_a', 'updated_ofa')

        # Feed it to a form and validate it
        form = self._get_form(NormalForm(instance=normal, prefix='normal', data=data),
                              OtherForm(instance=other, prefix='other', data=data),
                              data=data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form.forms['normal'].is_valid())
        self.assertTrue(form.forms['other'].is_valid())
        self.assertEqual(len(form.errors), 0)

        # Check cleaned data
        self.assertEqual(form.cleaned_data['normal.common'], 'updated_nc')
        self.assertEqual(form.cleaned_data['normal.field_a'], NORMAL[1].field_a)
        self.assertEqual(form.cleaned_data['other.common'], OTHER[1].common)
        self.assertEqual(form.cleaned_data['other.field_a'], 'updated_ofa')

        # Check changed data
        self.assertTrue(form.has_changed())
        self.assertCountEqual(form.changed_data, ('normal.common', 'other.field_a'))

        # Check the forms can be saved
        form.forms['normal'].save()
        form.forms['other'].save()
        self.assertEqual(normal.pk, self.normal_id[1])
        self.assertEqual(normal.common, 'updated_nc')
        self.assertEqual(normal.field_a, NORMAL[1].field_a)
        self.assertEqual(other.pk, self.other_id[1])
        self.assertEqual(other.common, OTHER[1].common)
        self.assertEqual(other.field_a, 'updated_ofa')

    def test_basic_proxy_validate_errors(self):
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[1])
        form = self._get_form(NormalForm(instance=normal, prefix='normal'),
                              OtherForm(instance=other, prefix='other'))

        # Get and alter html form data
        data = FormData(form)
        data.set_form_field(form, 'normal.common', '')
        data.set_form_field(form, 'other.field_a', 'updated_ofa')

        # Feed it to a form and validate it
        form = self._get_form(NormalForm(instance=normal, prefix='normal', data=data),
                              OtherForm(instance=other, prefix='other', data=data),
                              data=data)

        self.assertFalse(form.is_valid())
        self.assertFalse(form.forms['normal'].is_valid())
        self.assertTrue(form.forms['other'].is_valid())
        self.assertCountEqual(form.errors, ('normal.common',))

        # Check changed data
        self.assertTrue(form.has_changed())
        self.assertCountEqual(form.changed_data, ('normal.common', 'other.field_a'))


class BasicCompoundFormTest(NormalFixture, OtherFixture, TestCase):
    """ Compound forms are Proxy form that create and manage the proxied forms """
    normal_count = 1
    other_count = 1

    def _get_form(self, **kwargs):
        form_klass = compoundform_factory(
            OrderedDict((('normal', NormalForm), ('other', OtherForm))),
            base=MergingCompoundModelForm,
        )
        return form_klass(**kwargs)

    def test_basic_compound_create(self):
        """ Create an unbound compound form to check fields are mapped correctly """
        form = self._get_form()
        self.assertEqual(tuple(form.forms.keys()), ('normal', 'other'))
        self.assertCountEqual(form.fields,
                              ('normal.common', 'normal.field_a',
                               'other.common', 'other.field_a'))
        self.assertCountEqual((field.name for field in form),
                              ('common', 'field_a',
                               'common', 'field_a'))

        # Test the field are actually the same
        self.assertIs(form.fields['normal.common'], form.forms['normal'].fields['common'])
        self.assertIs(form.fields['normal.field_a'], form.forms['normal'].fields['field_a'])
        self.assertIs(form.fields['other.common'], form.forms['other'].fields['common'])
        self.assertIs(form.fields['other.field_a'], form.forms['other'].fields['field_a'])

        # Test sub-forms have prefixes
        self.assertEqual(form.forms['normal'].prefix, 'normal')
        self.assertEqual(form.forms['other'].prefix, 'other')

    def test_basic_compound_initial(self):
        """ Initialize the form with an instance on Normal and no Other """
        normal = Normal.objects.get(pk=self.normal_id[1])
        form = self._get_form(instances={'normal': normal})

        self.assertEqual(form['normal.common'].value(), NORMAL[1].common)
        self.assertEqual(form['normal.field_a'].value(), NORMAL[1].field_a)
        self.assertEqual(form['other.common'].value(), None)
        self.assertEqual(form['other.field_a'].value(), None)
        self.assertEqual(form.forms['normal']['common'].value(), NORMAL[1].common)
        self.assertEqual(form.forms['normal']['field_a'].value(), NORMAL[1].field_a)
        self.assertEqual(form.forms['other']['common'].value(), None)
        self.assertEqual(form.forms['other']['field_a'].value(), None)

    def test_basic_compound_validate(self):
        """ Update a Normal and create a new Other in one submission """
        normal = Normal.objects.get(pk=self.normal_id[1])
        form = self._get_form(instances={'normal': normal})

        # Get and alter html form data
        data = FormData(form)
        data.set_form_field(form, 'normal.common', 'updated_nc')
        data.set_form_field(form, 'other.common', 'created_oc')
        data.set_form_field(form, 'other.field_a', 'created_ofa')

        # Feed it to a form and validate it
        form = self._get_form(instances={'normal': normal}, data=data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form.forms['normal'].is_valid())
        self.assertTrue(form.forms['other'].is_valid())
        self.assertEqual(len(form.errors), 0)

        # Check the forms can be saved
        normal = form.forms['normal'].save()
        other = form.forms['other'].save()
        self.assertEqual(normal.pk, self.normal_id[1])
        self.assertEqual(normal.common, 'updated_nc')
        self.assertEqual(normal.field_a, NORMAL[1].field_a)
        self.assertNotIn(other.pk, (None,) + tuple(self.other_id.values()))
        self.assertEqual(other.common, 'created_oc')
        self.assertEqual(other.field_a, 'created_ofa')


class LinkedCompoundFormTest(NormalFixture, OtherFixture, TestCase):
    """ Compound forms with linked fields """
    normal_count = 1
    other_count = 1

    def _get_form(self, **kwargs):
        form = compoundform_factory(
            OrderedDict((('normal', NormalForm), ('other', OtherForm))),
            linked_fields=OrderedDict((('common', CharField(max_length=255, required=False)),)),
            base=MergingCompoundModelForm,
        )
        return form(**kwargs)

    def test_linked_compound_create(self):
        """ Create an unbound compound form to check fields are mapped correctly """
        form = self._get_form()
        self.assertEqual(tuple(form.forms.keys()), ('normal', 'other'))
        # Common field should shadow subform field of same name
        self.assertCountEqual(form.fields, ('common', 'normal.field_a', 'other.field_a'))
        self.assertCountEqual((field.name for field in form),
                              ('common', 'field_a', 'field_a'))

    def test_linked_compound_initial(self):
        # Test with matching instances
        assert NORMAL[1].common == OTHER[1].common, 'common field must match for same id'
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[1])

        # With matching linked fields, everything should be fine
        form = self._get_form(instances={'normal': normal, 'other': other})
        self.assertEqual(form['common'].value(), NORMAL[1].common)

        # With mismatched linked fields, ValueError should be raised
        with self.assertRaises(ValueError):
            form = self._get_form(instances={'normal': normal})

        # Specifiying an initial value manually should bypass pulling
        form = self._get_form(instances={'normal': normal},
                              initial={'common': 'common_force'})
        self.assertEqual(form['common'].value(), 'common_force')

        # Linked field should shadow subform's fields, including initial setting
        with self.assertRaises(ValueError):
            form = self._get_form(instances={'normal': normal},
                                  initial={'other.common': NORMAL[1].common})

    def test_linked_compound_validate_correct(self):
        """ Update a Normal and create a new Other in one submission """
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[1])
        form = self._get_form(instances={'normal': normal, 'other': other})

        # Get and alter html form data
        data = FormData(form)
        data.set_form_field(form, 'common', 'updated_common')
        data.set_form_field(form, 'other.field_a', 'updated_ofa')

        # Feed it to a form and validate it
        form = self._get_form(instances={'normal': normal, 'other': other}, data=data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form.forms['normal'].is_valid())
        self.assertTrue(form.forms['other'].is_valid())
        self.assertEqual(len(form.errors), 0)
        self.assertCountEqual(form.cleaned_data,
                              ('common', 'normal.field_a', 'other.field_a'))

        # Check changed data
        self.assertTrue(form.has_changed())
        self.assertCountEqual(form.changed_data, ('common', 'other.field_a'))

        # Check the forms can be saved
        normal = form.forms['normal'].save()
        other = form.forms['other'].save()
        self.assertEqual(normal.pk, self.normal_id[1])
        self.assertEqual(normal.common, 'updated_common')
        self.assertEqual(normal.field_a, NORMAL[1].field_a)
        self.assertEqual(other.pk, self.other_id[1])
        self.assertEqual(other.common, 'updated_common')
        self.assertEqual(other.field_a, 'updated_ofa')

    def test_linked_compound_validate_incorrect(self):
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[1])
        form = self._get_form(instances={'normal': normal, 'other': other})

        # Get and alter html form data
        data = FormData(form)
        data.set_form_field(form, 'common', '')

        # Feed it to a form and validate it
        form = self._get_form(instances={'normal': normal, 'other': other}, data=data)

        self.assertFalse(form.is_valid())
        self.assertFalse(form.forms['normal'].is_valid())
        self.assertFalse(form.forms['other'].is_valid())
        self.assertCountEqual(form.errors, ('common',))

        # Check changed data
        self.assertTrue(form.has_changed())
        self.assertCountEqual(form.changed_data, ('common',))
