from django.test import TestCase
from .data import NORMAL, NORMALREL, OTHER, OTHERREL
from .fixtures import (NormalFixture, NormalRelatedFixture,
                       OtherFixture, OtherRelatedFixture)
from app.models import Normal, NormalRelated, Other, OtherRelated

class SampleTest(NormalFixture, TestCase):
    normal_count = 2

    def test_proof(self):
        self.assertTrue(Normal.objects.count(), self.normal_count)
