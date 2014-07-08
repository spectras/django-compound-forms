from collections import namedtuple

#===============================================================================

NormalData = namedtuple('NormalData', 'common field_a')
NORMAL = {
    1: NormalData(common=u'common1', field_a=u'normal_a1'),
    2: NormalData(common=u'common2', field_a=u'normal_a2'),
}

NormalRelatedData = namedtuple('StandardData', 'common field_a normal')
NORMALREL = {
    1: NormalRelatedData(common=u'common1', field_a=u'normalrel_a1', normal=1),
    2: NormalRelatedData(common=u'common2', field_a=u'normalrel_a2', normal=2),
    3: NormalRelatedData(common=u'common3', field_a=u'normalrel_a3', normal=1),
    4: NormalRelatedData(common=u'common4', field_a=u'normalrel_a4', normal=2),
}

#===============================================================================

OtherData = namedtuple('OtherData', 'common field_a')
OTHER = {
    1: OtherData(common=u'common1', field_a=u'other_a1'),
    2: OtherData(common=u'common2', field_a=u'other_a2'),
}

OtherRelatedData = namedtuple('StandardData', 'common field_a other')
OTHERREL = {
    1: OtherRelatedData(common=u'common1', field_a=u'otherrel_a1', other=2),
    2: OtherRelatedData(common=u'common2', field_a=u'otherrel_a2', other=1),
    3: OtherRelatedData(common=u'common3', field_a=u'otherrel_a3', other=2),
    4: OtherRelatedData(common=u'common4', field_a=u'otherrel_a4', other=1),
}
