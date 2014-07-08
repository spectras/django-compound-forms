# -*- coding: utf-8 -*-
from .data import NORMAL, NORMALREL, OTHER, OTHERREL
from .utils import TestCase
from app.models import Normal, NormalRelated, Other, OtherRelated

class Fixture(TestCase):
    def setUp(self):
        self.create_fixtures()
        return super(Fixture, self).setUp()
    def create_fixtures(self):
        pass

#===============================================================================

class NormalFixture(Fixture):
    normal_count = 0

    def create_fixtures(self):
        super(NormalFixture, self).create_fixtures()
        assert self.normal_count <= len(NORMAL), 'Not enough fixtures in data'
        self.normal_id = {}
        for i in range(1, self.normal_count + 1):
            self.normal_id[i] = self.create_normal(NORMAL[i]).pk

    def create_normal(self, data):
        return Normal.objects.create(
            common=data.common,
            field_a=data.field_a
        )


class NormalRelatedFixture(NormalFixture):
    normalrel_count = 0

    def create_fixtures(self):
        super(NormalRelatedFixture, self).create_fixtures()
        assert self.normalrel_count <= len(NORMALREL)

        self.normalrel_id = {}
        for i in range(1, self.normalrel_count + 1):
            self.normalrel_id[i] = self.create_normalrel(NORMALREL[i]).pk

    def create_normalrel(self, data):
        return NormalRelated.objects.create(
            common=data.common,
            field_a=data.field_a,
            normal_id=self.normal_id[data.normal]
        )

#===============================================================================

class OtherFixture(Fixture):
    other_count = 0

    def create_fixtures(self):
        super(OtherFixture, self).create_fixtures()
        assert self.other_count <= len(OTHER), 'Not enough fixtures in data'
        self.other_id = {}
        for i in range(1, self.other_count + 1):
            self.other_id[i] = self.create_other(OTHER[i]).pk

    def create_other(self, data):
        return Other.objects.create(
            common=data.common,
            field_a=data.field_a
        )


class OtherRelatedFixture(OtherFixture):
    otherrel_count = 0

    def create_fixtures(self):
        super(OtherRelatedFixture, self).create_fixtures()
        assert self.otherrel_count <= len(OTHERREL)

        self.otherrel_id = {}
        for i in range(1, self.otherrel_count + 1):
            self.otherrel_id[i] = self.create_otherrel(OTHERREL[i]).pk

    def create_otherrel(self, data):
        return OtherRelated.objects.create(
            common=data.common,
            field_a=data.field_a,
            other_id=self.other_id[data.other]
        )

#===============================================================================
# Simple testing that fixture loading works

class FixtureTests(NormalRelatedFixture, NormalFixture,
                   OtherRelatedFixture, OtherFixture, TestCase):
    normal_count = len(NORMAL)
    normalrel_count = len(NORMALREL)
    other_count = len(OTHER)
    otherrel_count = len(OTHERREL)

    def test_fixtures(self):
        self.assertEqual(len(self.normal_id), self.normal_count)
        self.assertCountEqual(Normal.objects.values_list('id', flat=True),
                              self.normal_id.values())
        self.assertEqual(len(self.normalrel_id), self.normalrel_count)
        self.assertCountEqual(NormalRelated.objects.values_list('id', flat=True),
                              self.normalrel_id.values())
        self.assertEqual(len(self.other_id), self.other_count)
        self.assertCountEqual(Other.objects.values_list('id', flat=True),
                              self.other_id.values())
        self.assertEqual(len(self.otherrel_id), self.otherrel_count)
        self.assertCountEqual(OtherRelated.objects.values_list('id', flat=True),
                              self.otherrel_id.values())
