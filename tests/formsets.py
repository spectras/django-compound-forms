from django.forms import CharField
from django.test import TestCase
from collections import OrderedDict
from compound_forms.formsets import (ProxyFormSet, CompoundInlineFormSet,
                                     InvalidFormsetsError, compoundformset_factory)

from app.models import Normal, Other
from app.forms import (NormalFormset, NormalRelatedFormset,
                       OtherFormset, OtherRelatedFormset)
from .data import NORMAL, NORMALREL, OTHER, OTHERREL
from .fixtures import (NormalFixture, NormalRelatedFixture,
                       OtherFixture, OtherRelatedFixture)
from .formdata import FormData


class ProxyFormSetTests(NormalFixture, OtherFixture, TestCase):
    """ Proxy formsets act as proxy towards already existing formsets """
    item_count = 2
    normal_count = other_count = item_count

    def setUp(self):
        assert self.normal_count == self.other_count, 'querysets must have same length'
        assert NormalFormset.extra == OtherFormset.extra, 'subformsets must have same length'
        super(ProxyFormSetTests, self).setUp()

    def _get_formset(self, normal, other, **kwargs):
        ''' Helper function to build the form '''
        defaults = {
            'formsets': OrderedDict((('normal', normal), ('other', other),)),
            'formset_group_fields': OrderedDict((
                ('common', CharField(max_length=255, required=False)),
            )),
        }
        defaults.update(kwargs)
        return ProxyFormSet(**defaults)

    def test_proxy_create_valid(self):
        """ Test formsets are set on the proxy, and regular formset interface works """
        formset = self._get_formset(NormalFormset(queryset=Normal.objects.order_by('id')),
                                    OtherFormset())
        self.assertCountEqual(formset.formsets, ('normal', 'other'))

        self.assertEqual(len(formset.forms), self.item_count + NormalFormset.extra)
        self.assertEqual(formset.total_form_count(), self.item_count + NormalFormset.extra)
        self.assertEqual(len(formset.initial_forms), self.item_count)
        self.assertEqual(formset.initial_form_count(), self.item_count)
        self.assertEqual(len(formset.extra_forms), NormalFormset.extra)

        # Check forms content - grouping fields should have been made linked_fields
        for index, form in enumerate(formset.initial_forms, 1):
            self.assertCountEqual(form.forms, ('normal', 'other'))
            self.assertEqual(form['common'].value(), NORMAL[index].common)
            self.assertEqual(form['normal.field_a'].value(), NORMAL[index].field_a)
            self.assertEqual(form['other.field_a'].value(), OTHER[index].field_a)
            self.assertRaises(KeyError, form.__getitem__, 'normal.common')
            self.assertRaises(KeyError, form.__getitem__, 'other.common')
        for form in formset.extra_forms:
            self.assertCountEqual(form.forms, ('normal', 'other'))


    def test_proxy_create_invalid_number(self):
        """ Test an exception is raised if formset do not have same number of forms """
        formset = self._get_formset(NormalFormset(),
                                    OtherFormset(queryset=Other.objects.filter(
                                        pk=self.other_id[1]
                                    )))
        # the following must fail
        self.assertRaises(InvalidFormsetsError, formset.total_form_count)
        self.assertRaises(InvalidFormsetsError, formset.initial_form_count)
        self.assertRaises(InvalidFormsetsError, getattr, formset, 'forms')
        self.assertRaises(InvalidFormsetsError, formset.__getitem__, 'normal')
        self.assertRaises(InvalidFormsetsError, str, formset)
        #-- note: formset.is_valid() will not raise as the formset is not bound

    def test_proxy_create_shuffled(self):
        """ Test forms are correctly grouped despite not being in order on subformets """
        normalqs = Normal.objects.order_by('-common')
        formset = self._get_formset(NormalFormset(queryset=normalqs),
                                    OtherFormset(queryset=Other.objects.order_by('common')))
        self.assertCountEqual(formset.formsets, ('normal', 'other'))

        self.assertEqual(len(formset.forms), self.item_count + NormalFormset.extra)
        self.assertEqual(len(formset.initial_forms), self.item_count)
        self.assertEqual(len(formset.extra_forms), NormalFormset.extra)

        # for each initial form, test the grouping value is identical on all subforms
        # and that the order used is that of the first formset (NormalFormset here)
        for index, form in enumerate(formset.initial_forms):
            self.assertCountEqual(form.forms, ('normal', 'other'))
            self.assertTrue(all(subform['common'].value() == normalqs[index].common
                                for subform in form.forms.values()))

    def test_proxy_validate_correct(self):
        formset = self._get_formset(NormalFormset(queryset=Normal.objects.order_by('id'),
                                                  prefix='normal'),
                                    OtherFormset(prefix='other'))

        # Get and alter html formset data
        data = FormData(formset)
        data.set_formset_field(formset, 0, 'common', 'updated_common_1')
        data.set_formset_field(formset, 0, 'other.field_a', 'updated_ofa_1')

        # Feed it to a form and validate it
        formset = self._get_formset(NormalFormset(queryset=Normal.objects.order_by('id'),
                                                  data=data, prefix='normal'),
                                    OtherFormset(data=data, prefix='other'),
                                    data=data)
        self.assertTrue(formset.is_valid())
        self.assertTrue(formset.formsets['normal'].is_valid())
        self.assertTrue(formset.formsets['other'].is_valid())
        self.assertTrue(formset.forms[0].is_valid())
        self.assertTrue(formset.forms[1].is_valid())
        self.assertTrue(formset.forms[2].is_valid()) # valid because permitted empty
        self.assertEqual(formset.errors, [{}, {}, {}])
        self.assertTrue(formset.has_changed())

        # Check cleaned data
        self.assertEqual(len(formset.cleaned_data), 3)
        self.assertEqual(formset.cleaned_data[0]['common'], 'updated_common_1')
        self.assertEqual(formset.cleaned_data[0]['normal.field_a'], NORMAL[1].field_a)
        self.assertEqual(formset.cleaned_data[0]['other.field_a'], 'updated_ofa_1')
        self.assertEqual(formset.cleaned_data[0]['normal.id'].pk, self.normal_id[1])
        self.assertEqual(formset.cleaned_data[0]['other.id'].pk, self.other_id[1])
        self.assertEqual(formset.cleaned_data[1]['common'], NORMAL[2].common)
        self.assertEqual(formset.cleaned_data[1]['normal.field_a'], NORMAL[2].field_a)
        self.assertEqual(formset.cleaned_data[1]['other.field_a'], OTHER[2].field_a)
        self.assertEqual(formset.cleaned_data[1]['normal.id'].pk, self.normal_id[2])
        self.assertEqual(formset.cleaned_data[1]['other.id'].pk, self.other_id[2])
        self.assertEqual(len(formset.cleaned_data[2]), 0)

        # Test the formsets can be saved - no feature there but checking nothing
        # corrupted them along the way
        formset.formsets['normal'].save()
        formset.formsets['other'].save()
        obj = Normal.objects.get(pk=self.normal_id[1])
        self.assertEqual(obj.common, 'updated_common_1')
        self.assertEqual(obj.field_a, NORMAL[1].field_a)
        obj = Other.objects.get(pk=self.other_id[1])
        self.assertEqual(obj.common, 'updated_common_1')
        self.assertEqual(obj.field_a, 'updated_ofa_1')

    def test_proxy_validate_incorrect(self):
        formset = self._get_formset(NormalFormset(queryset=Normal.objects.order_by('id'),
                                                  prefix='normal'),
                                    OtherFormset(prefix='other'))

        # Get and alter html formset data
        data = FormData(formset)
        data.set_formset_field(formset, 0, 'common', '')
        data.set_formset_field(formset, 0, 'other.field_a', 'updated_ofa_1')
        data.set_formset_field(formset, 1, 'other.field_a', 'updated_ofa_2')

        # Feed it to a form and validate it
        formset = self._get_formset(NormalFormset(queryset=Normal.objects.order_by('id'),
                                                  data=data, prefix='normal'),
                                    OtherFormset(data=data, prefix='other'),
                                    data=data)
        self.assertFalse(formset.is_valid())
        self.assertFalse(formset.formsets['normal'].is_valid())
        self.assertFalse(formset.formsets['other'].is_valid())
        self.assertFalse(formset.forms[0].is_valid())
        self.assertTrue(formset.forms[1].is_valid())
        self.assertTrue(formset.forms[2].is_valid()) # valid because permitted empty
        self.assertCountEqual(formset.errors[0], ('common',))
        self.assertCountEqual(formset.errors[1], ())
        self.assertCountEqual(formset.errors[2], ())
        self.assertTrue(formset.has_changed())


class CompoundInlineFormSetTests(NormalRelatedFixture, NormalFixture,
                                 OtherRelatedFixture, OtherFixture, TestCase):
    """ Compound formsets manage the lifetime of their subformsets.
        Inline variant assumes those are all inline formsets
    """
    normal_count = other_count = 2
    normalrel_count = otherrel_count = 4

    def _get_formset(self, **kwargs):
        formset = compoundformset_factory(
            OrderedDict((
                ('normalrel', NormalRelatedFormset),
                ('otherrel', OtherRelatedFormset),
            )),
            base=CompoundInlineFormSet,
            formset_group_fields=OrderedDict((
                ('common', CharField(max_length=255, required=False)),
            )),
        )
        return formset(**kwargs)

    def test_compound_create(self):
        """ Test formsets are created correctly, and regular formset interface works """
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[2])
        formset = self._get_formset(instances={'normalrel': normal, 'otherrel': other})

        # Check basic formset structure
        self.assertCountEqual(formset.formsets, ('normalrel', 'otherrel'))
        #self.assertEqual(formset.formsets['normalrel'].prefix, 'normalrel')
        #self.assertEqual(formset.formsets['otherrel'].prefix, 'otherrel')
        self.assertEqual(len(formset.forms), 2 + NormalRelatedFormset.extra)
        self.assertEqual(formset.total_form_count(), 2 + NormalRelatedFormset.extra)
        self.assertEqual(len(formset.initial_forms), 2)
        self.assertEqual(formset.initial_form_count(), 2)
        self.assertEqual(len(formset.extra_forms), NormalRelatedFormset.extra)

        # Check instances where correctly assigned
        self.assertIs(formset.formsets['normalrel'].instance, normal)
        self.assertIs(formset.formsets['otherrel'].instance, other)

        # Check forms content - grouping fields should have been made linked_fields
        for index, form in enumerate(formset.initial_forms, 1):
            self.assertCountEqual(form.forms, ('normalrel', 'otherrel'))
            self.assertEqual(form['common'].value(), NORMALREL[2*index-1].common)
            self.assertEqual(form['normalrel.field_a'].value(), NORMALREL[2*index-1].field_a)
            self.assertEqual(form['otherrel.field_a'].value(), OTHERREL[2*index-1].field_a)
            self.assertRaises(KeyError, form.__getitem__, 'normalrel.common')
            self.assertRaises(KeyError, form.__getitem__, 'otherrel.common')
        for form in formset.extra_forms:
            self.assertCountEqual(form.forms, ('normalrel', 'otherrel'))

    def test_compound_save_update(self):
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[2])
        formset = self._get_formset(instances={'normalrel': normal, 'otherrel': other})

        data = FormData(formset)
        data.set_formset_field(formset, 0, 'common', 'updated_common_1')
        data.set_formset_field(formset, 0, 'normalrel.field_a', 'updated_fa_1')
        data.set_formset_field(formset, 1, 'otherrel.field_a', 'updated_fa_2')

        formset = self._get_formset(instances={'normalrel': normal, 'otherrel': other},
                                    data=data)

        self.assertTrue(formset.is_valid())
        formset.save()

        nrelqs = normal.related_set.order_by('id')
        orelqs = other.related_set.order_by('id')
        self.assertEqual(len(nrelqs), 2)
        self.assertEqual(len(orelqs), 2)

        self.assertEqual(nrelqs[0].common, 'updated_common_1')
        self.assertEqual(nrelqs[0].field_a, 'updated_fa_1')
        self.assertEqual(orelqs[0].common, 'updated_common_1')
        self.assertEqual(orelqs[0].field_a, OTHERREL[1].field_a)
        self.assertEqual(nrelqs[1].common, NORMALREL[3].common)
        self.assertEqual(nrelqs[1].field_a, NORMALREL[3].field_a)
        self.assertEqual(orelqs[1].common, OTHERREL[3].common)
        self.assertEqual(orelqs[1].field_a, 'updated_fa_2')


    def test_compound_save_delete(self):
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[2])
        formset = self._get_formset(instances={'normalrel': normal, 'otherrel': other})

        data = FormData(formset)
        data.set_formset_field(formset, 0, 'DELETE', 'on')

        formset = self._get_formset(instances={'normalrel': normal, 'otherrel': other},
                                    data=data)

        self.assertTrue(formset.is_valid())
        formset.save()

        nrelqs = normal.related_set.order_by('id')
        orelqs = other.related_set.order_by('id')
        self.assertEqual(len(nrelqs), 1)
        self.assertEqual(len(orelqs), 1)
        self.assertCountEqual(normal.related_set.values_list('id', flat=True),
                              (self.normalrel_id[3],))
        self.assertCountEqual(other.related_set.values_list('id', flat=True),
                              (self.otherrel_id[3],))

    def test_compound_save_create(self):
        normal = Normal.objects.get(pk=self.normal_id[1])
        other = Other.objects.get(pk=self.other_id[2])
        formset = self._get_formset(instances={'normalrel': normal, 'otherrel': other})

        data = FormData(formset)
        data.set_formset_field(formset, 2, 'common', 'created_common')
        data.set_formset_field(formset, 2, 'normalrel.field_a', 'created_nfa')
        data.set_formset_field(formset, 2, 'otherrel.field_a', 'created_ofa')

        formset = self._get_formset(instances={'normalrel': normal, 'otherrel': other},
                                    data=data)

        self.assertTrue(formset.is_valid())
        formset.save()

        nrelqs = normal.related_set.order_by('id')
        orelqs = other.related_set.order_by('id')
        self.assertEqual(len(nrelqs), 3)
        self.assertEqual(len(orelqs), 3)
