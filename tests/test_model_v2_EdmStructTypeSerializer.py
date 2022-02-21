"""Tests of OData Model: class VariableDeclaration"""

import pytest
import datetime
from pyodata.v2.model import EdmStructTypeSerializer, Types, StructType, StructTypeProperty
from pyodata.exceptions import PyODataException


@pytest.fixture
def complex_type_property_declarations():
    return {
        'TestString': (Types.parse_type_name('Edm.String'), "'FooBar'", "'FooBar'", 'FooBar'),
        'TestBoolean': (Types.parse_type_name('Edm.Boolean'), False, 'false', False),
        'TestInt64': (Types.parse_type_name('Edm.Int64'), '123L', '123L', 123),
        'TestDateTime': (Types.parse_type_name('Edm.DateTime'), "/Date(2147483647000)/", "datetime'2038-01-19T3:14:7'",
                         datetime.datetime(2038, 1, 19, hour=3, minute=14, second=7, tzinfo=datetime.timezone.utc))
    }


def define_complex_type(complex_type_property_declarations, nullable = True):
    complex_typ = StructType('TestComplexType', 'Label Complex Type', False)

    for name, prop_decl in complex_type_property_declarations.items():
        prop = StructTypeProperty(name, prop_decl[0], nullable, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, None)

        prop.typ = Types.from_name(prop.type_info.name)
        complex_typ._properties[prop.name] = prop
        prop.struct_type = complex_typ

    return complex_typ


@pytest.fixture
def complex_type_with_nullable_props(complex_type_property_declarations, nullable = True):
    return define_complex_type(complex_type_property_declarations, nullable=True)


@pytest.fixture
def complex_type_without_nullable_props(complex_type_property_declarations, nullable = True):
    return define_complex_type(complex_type_property_declarations, nullable=False)


def test_nullable_from_json_null_properties(complex_type_with_nullable_props, complex_type_property_declarations):
    entity_json = { prop_name: None for prop_name in complex_type_property_declarations.keys() }

    entity_odata = complex_type_with_nullable_props.traits.from_json(entity_json)

    assert entity_json.keys() == entity_odata.keys()

    for name, value in entity_odata.items():
        assert value is None, f'Property: {name}'


def test_non_nullable_from_json_null_properties(complex_type_without_nullable_props, complex_type_property_declarations):
    for prop_name in complex_type_property_declarations.keys():
        entity_json = { prop_name : None }
        with pytest.raises(PyODataException):
            entity_odata = complex_type_without_nullable_props.traits.from_json(entity_json)


def test_non_nullable_from_json(complex_type_without_nullable_props, complex_type_property_declarations):
    entity_json = { prop_name : prop_decl[1] for prop_name, prop_decl in complex_type_property_declarations.items() }

    entity_odata =complex_type_without_nullable_props.traits.from_json(entity_json)

    assert entity_json.keys() == entity_odata.keys()

    for name, value in entity_odata.items():
        assert value == complex_type_property_declarations[name][3], f'Value of {name}'


def test_nullable_from_literal_null_properties(complex_type_with_nullable_props, complex_type_property_declarations):
    entity_literal = { prop_name: None for prop_name in complex_type_property_declarations.keys() }

    entity_odata = complex_type_with_nullable_props.traits.from_literal(entity_literal)

    assert entity_literal.keys() == entity_odata.keys()

    for name, value in entity_odata.items():
        assert value is None, f'Property: {name}'


def test_non_nullable_from_literal_null_properties(complex_type_without_nullable_props, complex_type_property_declarations):
    for prop_name in complex_type_property_declarations.keys():
        entity_literal = { prop_name : None }
        with pytest.raises(PyODataException):
            entity_odata = complex_type_without_nullable_props.traits.from_literal(entity_literal)


def test_non_nullable_from_literal(complex_type_without_nullable_props, complex_type_property_declarations):
    entity_literal = { prop_name : prop_decl[2] for prop_name, prop_decl in complex_type_property_declarations.items() }

    entity_odata =complex_type_without_nullable_props.traits.from_literal(entity_literal)

    assert entity_literal.keys() == entity_odata.keys()

    for name, value in entity_odata.items():
        assert value == complex_type_property_declarations[name][3], f'Value of {name}'
