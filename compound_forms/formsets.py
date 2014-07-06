from django.core.exceptions import ValidationError
from django.forms.formsets import BaseFormSet
from django.utils.functional import cached_property
from collections import OrderedDict

from .forms import MergingProxyForm

##############################################################################

class SubFormSetsBuildMixin(BaseFormSet):
    formset_classes = OrderedDict()

    @cached_property
    def formsets(self):
        return OrderedDict((name, self._construct_formset(name))
                           for name in self.formset_classes.keys())

    def _construct_formset(self, name, **kwargs):
        klass = self.formset_classes[name]
        defaults = {
            'auto_id': self.auto_id,
            'prefix': self.add_prefix(name),
            'error_class': self.error_class,
        }
        if self.is_bound:
            defaults['data'] = self.data
            defaults['files'] = self.files
        if self.initial:
            defaults['initial'] = self.initial
        defaults.update(kwargs)
        return klass(**defaults)

##############################################################################

class ModelSubFormSetsMixin(SubFormSetsBuildMixin):
    def __init__(self, *args, **kwargs):
        self.instances = kwargs.pop('instances')
        super(ModelSubFormSetsMixin, self).__init__(*args, **kwargs)

    def _construct_formset(self, name, **kwargs):
        defaults = {
            'instance': self.instances.get(name),
        }
        defaults.update(kwargs)
        return super(ModelSubFormSetsMixin, self)._construct_formset(name, **defaults)

    def save(self, only=None, commit=True):
        keys = self.formsets.keys() if only is None else only
        return OrderedDict((name, self._save_formset(name, commit=commit)) for name in keys)

    def _save_formset(self, name, **kwargs):
        return self.formsets[name].save(**kwargs)

##############################################################################

class SubFormSetsProxyMixin(BaseFormSet):
    form = MergingProxyForm
    formset_group_fields = ()
    validate_max = False

    @property
    def management_form(self):
        forms = dict((name, formset.management_form) for name, formset in self.formsets.items())
        kwargs = {
            'forms': forms,
        }
        if self.is_bound:
            kwargs['data'] = self.data
            kwargs['files'] = self.files
        form = MergingProxyForm(**kwargs)
        if self.is_bound and not form.is_valid():
            raise ValidationError('Invalid management form')
        return form

    @cached_property
    def forms(self):
        #TODO: peek at initial data to guess the number beforehand and alter
        # subformset's management form TOTAL/extra
        groups, extras = OrderedDict(), []
        # Fill groups with forms from formsets
        first = True
        for formset_name, formset in self.formsets.items():
            for form in formset.initial_forms:
                key = tuple(form[field].field.initial
                            for field in self.formset_group_fields)
                if first:
                    groups[key] = {formset_name: form}
                else:   # ensure a mismatch key raises an exception
                    groups[key][formset_name] = form
            assert formset.initial_form_count() == len(groups), (
                '%s != %s' % (formset.initial_form_count(), len(groups)))

            for index, form in enumerate(formset.extra_forms):
                if first:
                    extras.append({formset_name: form})
                else:
                    extras[index][formset_name] = form
            assert index == len(extras)-1
            first = False

        linked_fields = list(self.formset_group_fields)
        if self.can_delete:
            linked_fields.append('DELETE')

        forms = (tuple(self._construct_form(i, forms=group, linked_fields=tuple(linked_fields))
                       for i, group in enumerate(groups.values()))
                 +
                 tuple(self._construct_form(i, forms=group, linked_fields=tuple(linked_fields))
                       for i, group in enumerate(extras, len(groups))))

        return forms

    def initial_form_count(self):
        count = next(iter(self.formsets.values())).initial_form_count()
        assert all(formset.initial_form_count() == count for formset in self.formsets.values())
        return count

    def total_form_count(self):
        count = next(iter(self.formsets.values())).total_form_count()
        assert all(formset.total_form_count() == count for formset in self.formsets.values())
        return count

    def full_clean(self):
        self._errors = []
        self._non_form_errors = self.error_class()
        if not self.is_bound:
            return

        for i in range(0, self.total_form_count()):
            self.forms[i].push_linked_fields()

        unique_non_form_errors = set()
        for formset in self.formsets.values():
            self._errors.append(formset.errors)
            unique_non_form_errors.update(formset.non_form_errors())
        self._non_form_errors.extend(unique_non_form_errors)

        for form in self.forms:
            self._errors.append(form.errors)
        try:
            self.clean()
        except ValidationError as e:
            self._non_form_errors = self.error_class(e.messages)

    @property
    def can_order(self):
        return all(formset.can_order for formset in self.formsets.values())

    @property
    def can_delete(self):
        return all(formset.can_delete for formset in self.formsets.values())

    @property
    def empty_form(self):
        form_list = tuple(formset.empty_form for formset in self.formsets.values())
        form = self.form(forms=form_list)
        self.add_fields(form, None)
        return form

##############################################################################

class ProxyFormSet(SubFormSetsProxyMixin, BaseFormSet):
    pass

class CompoundFormSet(SubFormSetsBuildMixin, SubFormSetsProxyMixin, BaseFormSet):
    pass

class CompoundModelFormSet(ModelSubFormSetsMixin, SubFormSetsProxyMixin, BaseFormSet):
    pass
