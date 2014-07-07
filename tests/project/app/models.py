import django
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Normal(models.Model):
    common = models.CharField(max_length=255)
    field_a = models.CharField(max_length=255)

    def __str__(self):
        return '<"%s", "%s">' % (self.field_a, self.field_b)


@python_2_unicode_compatible
class NormalRelated(models.Model):
    common = models.CharField(max_length=255)
    field_a = models.CharField(max_length=255)
    normal = models.ForeignKey(Normal, related_name='related_set', null=True)

    def __str__(self):
        return '"%s", "%s", <%r>' % (self.common, self.field_a, self.normal)

@python_2_unicode_compatible
class Other(models.Model):
    common = models.CharField(max_length=255)
    field_a = models.CharField(max_length=255)

    def __str__(self):
        return '"%s", "%s"' % (self.common, self.field_b)


@python_2_unicode_compatible
class OtherRelated(models.Model):
    common = models.CharField(max_length=255)
    field_a = models.CharField(max_length=255)
    other = models.ForeignKey(Other, related_name='related_set', null=True)

    def __str__(self):
        return '"%s", "%s", <%r>' % (self.common, self.field_a, self.other)