from django.core.exceptions import ValidationError
from django.forms.formsets import BaseFormSet
from django.utils.functional import cached_property
from collections import OrderedDict

from .forms import MergingProxyForm

##############################################################################

class InvalidFormsetsError(ValueError):
    pass

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

class InlineSubFormSetsMixin(SubFormSetsBuildMixin):
    def __init__(self, *args, **kwargs):
        self.instances = kwargs.pop('instances', {})
        super(InlineSubFormSetsMixin, self).__init__(*args, **kwargs)

    def _construct_formset(self, name, **kwargs):
        defaults = {
            'instance': self.instances.get(name),
        }
        defaults.update(kwargs)
        return super(InlineSubFormSetsMixin, self)._construct_formset(name, **defaults)

    def save(self, only=None, **kwargs):
        keys = self.formsets.keys() if only is None else only
        return OrderedDict((name, self._save_formset(name, **kwargs)) for name in keys)

    def _save_formset(self, name, **kwargs):
        return self.formsets[name].save(**kwargs)

##############################################################################

class SubFormSetsProxyMixin(BaseFormSet):
    form = MergingProxyForm
    formset_group_fields = OrderedDict()
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
            # Group initial forms by key (generated from fields in formset_group_fields)
            for form in formset.initial_forms:
                key = tuple(form.initial.get(field, form.fields[field].initial)
                            for field in self.formset_group_fields.keys())
                if first:
                    groups[key] = {formset_name: form}
                else:   # ensure a mismatch key raises an exception
                    groups[key][formset_name] = form

            # Check that formset grouping is correct
            if not first:
                if formset.initial_form_count() != len(groups):
                    raise InvalidFormsetsError(
                        'formsets do not have the same number of initial form groups: %d != %d',
                        formset.initial_form_count(), len(groups)
                    )
                if len(formset.extra_forms) != len(extras):
                    raise InvalidFormsetsError(
                        'formsets do not have the same number of extra forms: %d != %d',
                        len(formset.extra_forms), len(extras)
                    )

            # Simply group extra forms by their index
            for index, form in enumerate(formset.extra_forms):
                if first:
                    extras.append({formset_name: form})
                else:
                    extras[index][formset_name] = form

            first = False

        linked_fields = self.formset_group_fields.copy()
        if self.can_delete:
            linked_fields['DELETE'] = None

        forms = (tuple(self._construct_form(i, forms=group, linked_fields=linked_fields)
                       for i, group in enumerate(groups.values()))
                 +
                 tuple(self._construct_form(i, forms=group, linked_fields=linked_fields)
                       for i, group in enumerate(extras, len(groups))))
        return forms

    def initial_form_count(self):
        count = next(iter(self.formsets.values())).initial_form_count()
        if any(formset.initial_form_count() != count for formset in self.formsets.values()):
            raise InvalidFormsetsError('initial_form_count()s differ amongst sub-formsets')
        return count

    def total_form_count(self):
        count = next(iter(self.formsets.values())).total_form_count()
        if any(formset.total_form_count() != count for formset in self.formsets.values()):
            raise InvalidFormsetsError('total_form_count()s differ amongst sub-formsets')
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
            unique_non_form_errors.update(formset.non_form_errors())
            # do not add form errors as we will get them right after
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
    def __init__(self, *args, **kwargs):
        self.formsets = kwargs.pop('formsets')
        self.formset_group_fields = self.formset_group_fields.copy()
        self.formset_group_fields.update(kwargs.pop('formset_group_fields', {}))
        super(ProxyFormSet, self).__init__(*args, **kwargs)

class CompoundFormSet(SubFormSetsBuildMixin, SubFormSetsProxyMixin, BaseFormSet):
    pass

class CompoundInlineFormSet(InlineSubFormSetsMixin, SubFormSetsProxyMixin, BaseFormSet):
    pass
