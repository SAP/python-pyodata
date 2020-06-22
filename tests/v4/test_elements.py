import pytest

from pyodata.exceptions import PyODataException
from pyodata.v4.type_traits import EnumTypTrait


def test_enum_type(schema):
    gender = schema.enum_type('Gender')

    assert isinstance(gender.traits, EnumTypTrait)
    assert gender.is_flags is False
    assert gender.namespace == 'Microsoft.OData.SampleService.Models.TripPin'

    assert str(gender.Male) == "Gender'Male'"
    assert str(gender['Male']) == "Gender'Male'"
    assert str(gender[1]) == "Gender'Female'"
    assert gender.Male.parent == gender

    with pytest.raises(PyODataException) as ex_info:
        cat = gender.Cat
    assert ex_info.value.args[0] == 'EnumType EnumType(Gender) has no member Cat'

    with pytest.raises(PyODataException) as ex_info:
        who_knows = gender[15]
    assert ex_info.value.args[0] == 'EnumType EnumType(Gender) has no member with value 15'
