from django.forms import Form, ModelForm
from django.forms.forms import BaseForm, NON_FIELD_ERRORS
from django.utils.functional import cached_property
from collections import OrderedDict

##############################################################################

class SubFormsProxyMixin(BaseForm):
    """ Base form that handles sub-forms with optional linked fields """
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
        self.instances = kwargs.pop('instances')
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

class LinkedFieldsMixin(BaseForm):
    linked_fields = ()

    def push_linked_fields(self):
        assert (field in self.fields for field in self.linked_fields)
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
        super(LinkedFieldsMixin, self).full_clean()

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
                if field_name in getattr(self, 'linked_fields', ()):
                    continue
                alias = self._get_alias(form_name, field_name)
                self.fields[alias] = field
                self.field_form[alias] = (form, field_name)

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
            self._errors.update((NON_FIELD_ERRORS if name == NON_FIELD_ERRORS else
                                self._get_alias(form_name, name), errors)
                                for name, errors in form.errors.items())
            self.cleaned_data.update((self._get_alias(form_name, name), data)
                                        for name, data in form.cleaned_data.items())

    @property
    def changed_data(self):
        """ Merge in subform's changed_data """
        ret = super(MergingFormMixin, self).changed_data
        for form_name, form in self.forms.items():
            ret.extend(self._get_alias(form_name, name) for name in form.changed_data)
        return ret

    def _get_alias(self, form_name, field_name):
        """ Compute the alias for a given form and field names """
        return '%s.%s' % (form_name, field_name)

##############################################################################

class BaseProxyForm(SubFormsProxyMixin, LinkedFieldsMixin):
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

class BaseCompoundForm(SubFormsBuildMixin, SubFormsProxyMixin, LinkedFieldsMixin):
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
