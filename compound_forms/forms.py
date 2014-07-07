from django.forms import Form, ModelForm
from django.forms.forms import BaseForm, NON_FIELD_ERRORS
from django.utils.functional import cached_property
from collections import OrderedDict

##############################################################################

class SubFormsProxyMixin(BaseForm):
    """ Base form that handles sub-forms with optional linked fields """
    linked_fields = ()

    def __init__(self, *args, **kwargs):
        super(SubFormsProxyMixin, self).__init__(*args, **kwargs)
        self.pull_linked_fields()

    def pull_linked_fields(self):
        """ Pull initial values from sub-forms (and checks they are identical) """
        assert (field in self.fields for field in self.linked_fields)
        if not self.is_bound:
            for name in self.linked_fields:
                if name in self.initial: # if an initial value is explicitly
                    continue             # specified, simply use it
                initials = tuple(
                    form.initial.get(name, form.fields[name].initial)
                    for form in self.forms.values()
                    if name in form.fields
                )
                if initials.count(initials[0]) != len(initials):
                    raise ValueError('Initial sub-form values differ for '
                                     'linked field %s: %r' % (name, initials))
                self.initial[name] = initials[0]

    def push_linked_fields(self):
        """ Push raw field data to sub-forms and let them do the cleaning later """
        assert (field in self.fields for field in self.linked_fields)
        if self.is_bound:
            for form in self.forms.values():
                form.data = form.data.copy() # we need a mutable copy
                form.data.update(dict(
                    (form.add_prefix(name), self._raw_value(name))
                    for name in self.linked_fields
                    if name in form.fields
                ))

    def full_clean(self):
        if self.is_bound:
            self.push_linked_fields()
        super(SubFormsProxyMixin, self).full_clean()

    def is_valid(self):
        return (super(SubFormsProxyMixin, self).is_valid() and
                all(form.is_valid() for form in self.forms.values()))

    def has_changed(self):
        return (super(SubFormsProxyMixin, self).has_changed() or
                any(form.has_changed() for form in self.forms.values()))

    @property
    def media(self):
        return (super(SubFormsProxyMixin, self).media +
                sum(form.media for form in self.forms.values()))

    def is_multipart(self):
        return (super(SubFormsProxyMixin, self).is_multipart() or
                any(form.is_multipart() for form in self.forms.values()))

##############################################################################

class SubFormsBuildMixin(BaseForm):
    form_classes = OrderedDict()

    @cached_property
    def forms(self):
        """ Dict of name: form """
        return OrderedDict((name, self._construct_form(name)) for name in self.form_classes.keys())

    def _construct_form(self, name, **kwargs):
        klass = self.form_classes[name]
        defaults = {
            'auto_id': self.auto_id,
            'prefix': self.add_prefix(name),
            'error_class': self.error_class,
        }
        if self.is_bound:
            defaults['data'] = self.data
            defaults['files'] = self.files
        if self.initial and not 'initial' in kwargs:
            try:
                defaults['initial'] = self.initial[name]
            except KeyError:
                pass
        defaults.update(kwargs)
        return klass(**defaults)

##############################################################################

class ModelSubFormsMixin(BaseForm):
    def __init__(self, *args, **kwargs):
        self.instances = kwargs.pop('instances', {})
        super(ModelSubFormsMixin, self).__init__(*args, **kwargs)

    def _construct_form(self, name, **kwargs):
        defaults = {
            'instance': self.instances.get(name),
        }
        defaults.update(kwargs)
        return super(ModelSubFormsMixin, self)._construct_form(name, **defaults)

    def save(self, only=None, commit=True):
        keys = self.forms.keys() if only is None else only
        return OrderedDict((name, self._save_form(name, commit=commit)) for name in keys)

    def _save_form(self, name, **kwargs):
        return self.forms[name].save(**kwargs)

##############################################################################

class MergingFormMixin(BaseForm):
    """ A BaseCompoundForm that allows access to subforms through field aliases """
    def __init__(self, *args, **kwargs):
        super(MergingFormMixin, self).__init__(*args, **kwargs)
        self.field_form = {}
        self._make_field_aliases()

    def _make_field_aliases(self):
        for form_name, form in self.forms.items():
            for field_name, field in form.fields.items():
                if field_name in self.linked_fields:
                    continue
                alias = self._get_alias(form_name, field_name)
                self.fields[alias] = field
                self.field_form[alias] = (form, field_name)

    def _construct_form(self, name, **kwargs):
        defaults = {}
        if 'initial' in kwargs: # extract initial for this form
            initial = {}
            for key, value in kwargs['initial'].items():
                try:
                    form_name, field_name = key.split('.')
                except ValueError:
                    continue
                if form_name == name and field_name not in self.linked_fields:
                    initial[field_name] = value
            defaults['initial'] = initial
        defaults.update(kwargs)
        return super(MergingFormMixin, self)._construct_form(name, **defaults)

    def __getitem__(self, name):
        """ Retrieve the field by name, merging own field with content form's """
        if name in self.field_form:
            form, field_name = self.field_form[name]
            return form.__getitem__(field_name)
        return super(MergingFormMixin, self).__getitem__(name)

    def _clean_fields(self):
        """ Omit merged fields from _clean_fields, as they would be seen as all empty """
        fields = self.fields
        self.fields = dict((k, v) for k, v in fields.items() if not k in self.field_form)
        super(MergingFormMixin, self)._clean_fields()
        self.fields = fields

    def _clean_form(self):
        """ Merge in subform errors and cleaned_data under their alias names """
        super(MergingFormMixin, self)._clean_form()
        for form_name, form in self.forms.items():
            for field_name, errors in form.errors.items():
                if field_name != NON_FIELD_ERRORS:
                    field_name = self._get_alias(form_name, field_name)
                self._errors.setdefault(field_name, set()).update(errors)
            self.cleaned_data.update((self._get_alias(form_name, name), data)
                                     for name, data in form.cleaned_data.items()
                                     if name not in self.linked_fields)

    @property
    def changed_data(self):
        """ Merge in subform's changed_data """
        if self._changed_data is None:
            ret = set(super(MergingFormMixin, self).changed_data)
            for form_name, form in self.forms.items():
                ret.update(self._get_alias(form_name, name) for name in form.changed_data)
            self._changed_data = tuple(ret)
        return self._changed_data

    def _get_alias(self, form_name, field_name):
        """ Compute the alias for a given form and field names """
        if field_name in self.linked_fields:
            return field_name
        return '%s.%s' % (form_name, field_name)

##############################################################################

class BaseProxyForm(SubFormsProxyMixin):
    """ Compound form that proxies fields to its subforms """
    def __init__(self, *args, **kwargs):
        self.forms = kwargs.pop('forms')
        self.linked_fields = self.linked_fields + kwargs.pop('linked_fields', ())
        super(BaseProxyForm, self).__init__(*args, **kwargs)

class BaseMergingProxyForm(MergingFormMixin, BaseProxyForm):
    pass

class ProxyForm(Form, BaseProxyForm):
    pass

class MergingProxyForm(Form, BaseMergingProxyForm):
    pass


class BaseCompoundForm(SubFormsBuildMixin, SubFormsProxyMixin):
    """ Compound form that builds subforms and proxies fields to them """
    pass

class BaseMergingCompoundForm(MergingFormMixin, BaseCompoundForm):
    pass

class CompoundForm(Form, BaseCompoundForm):
    pass

class CompoundModelForm(Form, ModelSubFormsMixin, BaseCompoundForm):
    pass

class MergingCompoundForm(Form, BaseMergingCompoundForm):
    pass

class MergingCompoundModelForm(Form, ModelSubFormsMixin, BaseMergingCompoundForm):
    pass

def compoundform_factory(forms, base=MergingCompoundForm, linked_fields=None):
    attrs = {
        'form_classes': forms,
    }
    if linked_fields is not None:
        attrs['linked_fields'] = linked_fields
    return type(base.__name__, (base,), attrs)
