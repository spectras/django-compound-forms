from django.forms.models import (modelform_factory, modelformset_factory,
                                 inlineformset_factory)
from .models import Normal, NormalRelated, Other, OtherRelated

NormalForm = modelform_factory(Normal, exclude=[])
NormalRelatedForm = modelform_factory(NormalRelated, exclude=[])
OtherForm = modelform_factory(Other, exclude=[])
OtherRelatedForm = modelform_factory(OtherRelated, exclude=[])

NormalFormset = modelformset_factory(Normal, form=NormalForm, extra=1)
NormalRelatedFormset = inlineformset_factory(Normal, NormalRelated,
                                             form=NormalRelatedForm, extra=1)
OtherFormset = modelformset_factory(Other, form=OtherForm, extra=1)
OtherRelatedFormset = inlineformset_factory(Other, OtherRelated,
                                            form=OtherRelatedForm, extra=1)
