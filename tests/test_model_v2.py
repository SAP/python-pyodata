"""Tests for OData Model module"""
# pylint: disable=line-too-long,too-many-locals,too-many-statements,invalid-name, too-many-lines, no-name-in-module, expression-not-assigned, pointless-statement
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from pyodata.v2.model import Schema, Typ, StructTypeProperty, Types, EntityType, EdmStructTypeSerializer, \
    Association, AssociationSet, EndRole, AssociationSetEndRole, TypeInfo, MetadataBuilder, ParserError, PolicyWarning, \
    PolicyIgnore, Config, PolicyFatal, NullType, NullAssociation, StructType, parse_datetime_literal
from pyodata.exceptions import PyODataException, PyODataModelError, PyODataParserError
from tests.conftest import assert_logging_policy
import pyodata.v2.model


def test_edmx(schema):
    """Test Edmx class"""

    # pylint: disable=redefined-outer-name

    assert set(schema.namespaces) == {'EXAMPLE_SRV', 'EXAMPLE_SRV_SETS'}

    assert set((entity_type.name for entity_type in schema.entity_types)) == {
        'Address',
        'MasterEntity',
        'DataEntity',
        'Employee',
        'AnnotationTest',
        'City',
        'TemperatureMeasurement',
        'Car',
        'CarIDPic',
        'Customer',
        'Order',
        'EnumTest',
        'Enumeration',
        'MaterialEntityWithEmptyString',
    }

    assert set((entity_set.name for entity_set in schema.entity_sets)) == {
        'Addresses',
        'Employees',
        'MasterEntities',
        'DataValueHelp',
        'Cities',
        'CitiesNotAddressable',
        'CitiesWithFilter',
        'TemperatureMeasurements',
        'Cars',
        'CarIDPics',
        'Customers',
        'Orders',
        'EnumTests',
        'Enumerations'
    }

    assert set((enum_type.name for enum_type in schema.enum_types)) == {
        'Country',
        'Language'
    }

    master_entity = schema.entity_type('MasterEntity')
    assert str(master_entity) == 'EntityType(MasterEntity)'
    assert master_entity.name == 'MasterEntity'
    assert master_entity.label is None
    assert not master_entity.is_value_list
    assert sorted([p.name for p in master_entity.proprties()]) == ['Data', 'DataName', 'DataType', 'Key']

    master_entity_set = schema.entity_set('MasterEntities')
    assert master_entity_set.label == 'Master entities'

    data_entity = schema.entity_type('DataEntity')
    assert str(data_entity) == 'EntityType(DataEntity)'
    assert data_entity.name == 'DataEntity'
    assert data_entity.label == 'Data entities'
    assert data_entity.is_value_list
    assert not data_entity.proprty('Invisible').visible

    master_prop_key = master_entity.proprty('Key')
    assert str(master_prop_key) == 'StructTypeProperty(Key)'
    assert str(master_prop_key.struct_type) == 'EntityType(MasterEntity)'
    assert master_prop_key.value_helper is None
    assert master_prop_key.value_list == 'standard'

    master_prop_data = master_entity.proprty('Data')
    assert master_prop_data.text_proprty.name == 'DataName'
    assert master_prop_data.visible
    assert master_prop_data.max_length == StructTypeProperty.MAXIMUM_LENGTH

    master_prop_data_vh = master_prop_data.value_helper
    assert str(master_prop_data_vh) == 'ValueHelper(MasterEntity/Data)'
    assert str(master_prop_data_vh.proprty) == 'StructTypeProperty(Data)'

    assert str(master_prop_data_vh.entity_set) == 'EntitySet(DataValueHelp)'
    assert str(master_prop_data_vh.entity_set.entity_type) == 'EntityType(DataEntity)'

    vh_prm_data_type = master_prop_data_vh.local_property_param('DataType')
    assert str(vh_prm_data_type) == 'ValueHelperParameter(DataType=Type)'
    assert str(vh_prm_data_type.local_property) == 'StructTypeProperty(DataType)'
    assert str(vh_prm_data_type.list_property) == 'StructTypeProperty(Type)'

    vh_prm_description = master_prop_data_vh.list_property_param('Description')
    assert str(vh_prm_description) == 'ValueHelperParameter(Description)'
    assert str(vh_prm_description.list_property.struct_type) == 'EntityType(DataEntity)'

    annotation_test = schema.entity_type('AnnotationTest')
    no_format_prop = annotation_test.proprty('NoFormat')
    assert not no_format_prop.upper_case
    assert not no_format_prop.date
    assert not no_format_prop.non_negative

    upper_case_prop = annotation_test.proprty('UpperCase')
    assert upper_case_prop.upper_case
    assert not upper_case_prop.date
    assert not upper_case_prop.non_negative

    date_prop = annotation_test.proprty('Date')
    assert not date_prop.upper_case
    assert date_prop.date
    assert not date_prop.non_negative

    non_negative_prop = annotation_test.proprty('NonNegative')
    assert not non_negative_prop.upper_case
    assert not non_negative_prop.date
    assert non_negative_prop.non_negative

    car_entity = schema.entity_type('Car')
    assert car_entity.proprty('CodeName').filter_restriction == 'single-value'
    assert car_entity.proprty('CodeName').required_in_filter
    assert not car_entity.proprty('Price').required_in_filter

    price_prop = car_entity.proprty('Price')
    assert price_prop.precision == 7
    assert price_prop.scale == 3

    # EntityType from the method typ
    assert schema.typ('MasterEntity') == schema.entity_type('MasterEntity')
    assert schema.typ('MasterEntity', namespace='EXAMPLE_SRV') == schema.entity_type('MasterEntity',
                                                                                     namespace='EXAMPLE_SRV')
    # check that the collection of this EntityType was generated
    assert schema.typ('Collection(MasterEntity)', namespace='EXAMPLE_SRV') == schema._collections_entity_types('Collection(MasterEntity)',
                                                                                     namespace='EXAMPLE_SRV')

    # ComplexType from the method typ
    assert schema.typ('Building') == schema.complex_type('Building')
    assert schema.typ('Building', namespace='EXAMPLE_SRV') == schema.complex_type('Building', namespace='EXAMPLE_SRV')

    # check that the collection of this ComplexType was generated
    assert schema.typ('Collection(Building)', namespace='EXAMPLE_SRV') == schema._collections_complex_types(
                                            'Collection(Building)',namespace='EXAMPLE_SRV')

    # Error handling in the method typ - without namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.typ('FooBar')
    assert typ_ex_info.value.args[0] == 'Type FooBar does not exist in Schema'
    # Error handling in the method typ - with namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.typ('FooBar', namespace='EXAMPLE_SRV')
    assert typ_ex_info.value.args[0] == 'Type FooBar does not exist in Schema Namespace EXAMPLE_SRV'


def test_schema_entity_type_nullable(schema):
    emp_entity = schema.entity_type('Employee')

    id_property = emp_entity.proprty('ID')
    assert not id_property.nullable

    firstname_property = emp_entity.proprty('NameFirst')
    assert firstname_property.nullable

    nickname_property = emp_entity.proprty('NickName')
    assert nickname_property.nullable


@pytest.mark.parametrize('property_name,is_fixed_length,comment', [
    ('Name', False, 'Name has no FixedLength property, defaults to false'),
    ('ID', True, 'Customer ID length is fixed'),
    ('City', False, 'City names have arbitrary lengths'),
])
def test_schema_entity_type_fixed_length(schema, property_name, is_fixed_length, comment):
    customer_entity = schema.entity_type('Customer')

    property_ = customer_entity.proprty(property_name)
    assert property_.fixed_length == is_fixed_length, comment


def test_schema_entity_sets(schema):
    """Test Schema methods for EntitySets"""

    for entity_set in schema.entity_sets:
        assert schema.entity_set(entity_set.name) == entity_set

    assert schema.entity_set('Cities', namespace='EXAMPLE_SRV') is not None

    # without namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.entity_set('FooBar')
    assert typ_ex_info.value.args[0] == 'EntitySet FooBar does not exist in any Schema Namespace'

    # with unknown namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.entity_set('FooBar', namespace='BLAH')
    assert typ_ex_info.value.args[0] == 'EntitySet FooBar does not exist in Schema Namespace BLAH'

    # with namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.entity_set('FooBar', namespace='EXAMPLE_SRV')
    assert typ_ex_info.value.args[0] == 'EntitySet FooBar does not exist in Schema Namespace EXAMPLE_SRV'


def test_edmx_associations(schema):
    """Test parsing of associations and association sets"""

    assert set((association.name for association in schema.associations)) == {
        'toCarIDPic',
        'toDataEntity',
        'CustomerOrders',
        'CustomerReferredBy',
        'AssociationEmployeeAddress',
        'toSelfMaster'
    }

    association = schema.association('toDataEntity')
    assert str(association) == 'Association(toDataEntity)'

    from_role = association.end_by_role('FromRole_toDataEntity')
    assert from_role.multiplicity == '1'
    assert str(from_role.entity_type) == 'EntityType(MasterEntity)'

    to_role = association.end_by_role('ToRole_toDataEntity')
    assert to_role.multiplicity == '*'
    assert str(to_role.entity_type) == 'EntityType(DataEntity)'

    principal_role = association.referential_constraint.principal
    assert principal_role.name == 'FromRole_toDataEntity'
    assert principal_role.property_names == ['Key']

    dependent_role = association.referential_constraint.dependent
    assert dependent_role.name == 'ToRole_toDataEntity'
    assert dependent_role.property_names == ['Name']

    assert set((association_set.name for association_set in schema.association_sets)) == {
        'toDataEntitySet',
        'AssociationEmployeeAddress_AssocSet',
        'CustomerOrder_AssocSet',
        'CustomerReferredBy_AssocSet',
        'toCarIDPicSet',
        'toSelfMasterSet'
    }

    association_set = schema.association_set('toDataEntitySet')
    assert str(association_set) == 'AssociationSet(toDataEntitySet)'
    assert association_set.association_type.name == 'toDataEntity'

    # check associated references to entity sets
    association_set = schema.association_set('toDataEntitySet')
    entity_sets = {end.entity_set.name for end in association_set.end_roles}
    assert entity_sets == {'MasterEntities', 'DataValueHelp'}

    end_roles = {(end.entity_set_name, end.role) for end in association_set.end_roles}
    assert end_roles == {('DataValueHelp', 'ToRole_toDataEntity'), ('MasterEntities', 'FromRole_toDataEntity')}

    # same entity sets in different ends
    association_set = schema.association_set('toSelfMasterSet')
    assert str(association_set) == 'AssociationSet(toSelfMasterSet)'
    end_roles = {(end.entity_set_name, end.role) for end in association_set.end_roles}
    assert end_roles == {('MasterEntities', 'ToRole_toSelfMaster'), ('MasterEntities', 'FromRole_toSelfMaster')}

    # with namespace
    association_set = schema.association_set_by_association('CustomerOrders', namespace='EXAMPLE_SRV_SETS')
    assert str(association_set) == 'AssociationSet(CustomerOrder_AssocSet)'

    # without namespace
    association_set = schema.association_set_by_association('CustomerOrders')
    assert str(association_set) == 'AssociationSet(CustomerOrder_AssocSet)'

    # error handling: without namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.association_set_by_association('FooBar')
    assert typ_ex_info.value.args[0] == 'Association Set for Association FooBar does not exist in any Schema Namespace'

    # error handling: with unknown namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.association_set_by_association('FooBar', namespace='BLAH')
    assert typ_ex_info.value.args[0] == 'There is no Schema Namespace BLAH'

    # error handling: with namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.association_set_by_association('FooBar', namespace='EXAMPLE_SRV')
    assert typ_ex_info.value.args[0] == 'Association Set for Association FooBar does not exist in Schema Namespace EXAMPLE_SRV'


def test_edmx_navigation_properties(schema):
    """Test parsing of navigation properties"""

    emp_entity = schema.entity_type('Employee')
    assert str(emp_entity) == 'EntityType(Employee)'
    assert emp_entity.name == 'Employee'

    nav_prop = emp_entity.nav_proprty('Addresses')
    assert str(nav_prop) == 'NavigationTypeProperty(Addresses)'
    assert str(nav_prop.to_role) == 'EndRole(AddressRole)'
    assert str(nav_prop.to_role.entity_type) == 'EntityType(Address)'


def test_edmx_function_imports(schema):
    """Test parsing of function imports"""

    assert set((func_import.name for func_import in schema.function_imports)) == {'get_best_measurements', 'retrieve',
                                                                                  'get_max', 'sum', 'sum_complex', 'refresh'}
    # pylint: disable=redefined-outer-name

    function_import = schema.function_import('retrieve')
    assert str(function_import) == 'FunctionImport(retrieve)'
    assert function_import.name == 'retrieve'
    assert function_import.return_type.name == 'Edm.Boolean'
    assert function_import.entity_set_name == 'MasterEntities'
    assert function_import.http_method == 'GET'

    param = function_import.parameters[0]
    assert str(param) == 'FunctionImportParameter(Param)'
    assert param.name == 'Param'
    assert param.typ.name == 'Edm.String'
    assert not param.nullable
    assert param.max_length is None
    assert param.mode == 'In'
    assert param.typ.traits.to_literal('Foo') == "'Foo'"
    assert param.typ.traits.from_literal("'Foo'") == 'Foo'

    # function import without return type
    function_import = schema.function_import('refresh')
    assert function_import.return_type is None
    assert function_import.http_method == 'GET'

    # function import that returns entity
    function_import = schema.function_import('get_max')
    assert str(function_import) == 'FunctionImport(get_max)'
    assert function_import.name == 'get_max'
    assert repr(function_import.return_type) == 'EntityType(TemperatureMeasurement)'
    assert function_import.return_type.kind == Typ.Kinds.Complex
    assert repr(function_import.return_type.traits) == 'EdmStructTypTraits'
    assert function_import.entity_set_name == 'TemperatureMeasurements'
    assert function_import.http_method == 'GET'

    # function import that returns collection of entities
    function_import = schema.function_import('get_best_measurements')
    assert str(function_import) == 'FunctionImport(get_best_measurements)'
    assert function_import.name == 'get_best_measurements'
    assert repr(function_import.return_type) == 'Collection(EntityType(TemperatureMeasurement))'
    assert function_import.return_type.kind == Typ.Kinds.Complex
    assert function_import.return_type.is_collection
    assert repr(function_import.return_type.traits) == 'Collection(EntityType(TemperatureMeasurement))'
    assert function_import.http_method == 'GET'


def test_edmx_complex_types(schema):
    """Test parsing of complex types"""

    # pylint: disable=redefined-outer-name

    assert set(schema.namespaces) == {'EXAMPLE_SRV', 'EXAMPLE_SRV_SETS'}

    assert set((complex_type.name for complex_type in schema.complex_types)) == {'Building', 'ComplexNumber',
                                                                                 'Rectangle'}

    complex_number = schema.complex_type('ComplexNumber')
    assert str(complex_number) == 'ComplexType(ComplexNumber)'
    assert complex_number.name == 'ComplexNumber'
    assert sorted([p.name for p in complex_number.proprties()]) == ['Imaginary', 'Real']

    real_prop = complex_number.proprty('Real')
    assert str(real_prop) == 'StructTypeProperty(Real)'
    assert str(real_prop.struct_type) == 'ComplexType(ComplexNumber)'

    # after correct parsing, new complex type is registered in metadata schema
    assert str(schema.typ('ComplexNumber')) == 'ComplexType(ComplexNumber)'
    assert str(schema.typ('Collection(ComplexNumber)')) == 'Collection(ComplexNumber)'

def test_edmx_complex_type_prop_vh(schema):
    """Check that value helpers work also for ComplexType properties and aliases"""

    building = schema.complex_type('Building')
    city_prop = building.proprty('City')
    city_prop_vh = city_prop.value_helper

    assert city_prop_vh is not None
    assert city_prop_vh.proprty.name == 'City'
    assert city_prop_vh.entity_set.name == 'Cities'
    assert city_prop_vh.entity_set.entity_type.name == 'City'


def test_traits():
    """Test individual traits"""

    # generic
    typ = Types.from_name('Edm.Byte')
    assert repr(typ.traits) == 'TypTraits'
    assert typ.traits.to_literal('85') == '85'
    assert typ.traits.from_literal('170') == '170'

    # binary
    typ = Types.from_name('Edm.Binary')
    assert repr(typ.traits) == 'EdmBinaryTypTraits'
    assert typ.traits.to_literal('wAHK/rqt8A0=') == 'binary\'C001CAFEBAADF00D\''
    assert typ.traits.from_literal('binary\'C001cafeBAADF00D\'') == 'wAHK/rqt8A0='
    assert typ.traits.from_literal('X\'C001cafeBAADF00D\'') == 'wAHK/rqt8A0='
    assert typ.traits.to_json('cHlvZGF0YQ==') == 'cHlvZGF0YQ=='
    assert typ.traits.from_json('cHlvZGF0YQ==') == 'cHlvZGF0YQ=='

    # string
    typ = Types.from_name('Edm.String')
    assert repr(typ.traits) == 'EdmStringTypTraits'
    assert typ.traits.to_literal('Foo Foo') == "'Foo Foo'"
    assert typ.traits.from_literal("'Alice Bob'") == 'Alice Bob'

    # bool
    typ = Types.from_name('Edm.Boolean')
    assert repr(typ.traits) == 'EdmBooleanTypTraits'
    assert typ.traits.to_literal(True) == 'true'
    assert typ.traits.from_literal('true') is True
    assert typ.traits.to_literal(False) == 'false'
    assert typ.traits.from_literal('false') is False
    assert typ.traits.to_literal(1) == 'true'
    assert typ.traits.to_literal(0) == 'false'

    assert typ.traits.from_json(True) is True
    assert typ.traits.from_json(False) is False

    # integers
    typ = Types.from_name('Edm.Int16')
    assert repr(typ.traits) == 'EdmIntTypTraits'
    assert typ.traits.to_literal(23) == '23'
    assert typ.traits.from_literal('345') == 345

    typ = Types.from_name('Edm.Int32')
    assert repr(typ.traits) == 'EdmIntTypTraits'
    assert typ.traits.to_literal(23) == '23'
    assert typ.traits.from_literal('345') == 345

    typ = Types.from_name('Edm.Int64')
    assert repr(typ.traits) == 'EdmLongIntTypTraits'
    assert typ.traits.to_literal(23) == '23L'
    assert typ.traits.from_literal('345L') == 345
    assert typ.traits.from_json('345L') == 345
    assert typ.traits.from_literal('345') == 345
    assert typ.traits.from_json('345') == 345
    assert typ.traits.from_literal('0') == 0
    assert typ.traits.from_json('0') == 0
    assert typ.traits.from_literal('0L') == 0
    assert typ.traits.from_json('0L') == 0

    typ = Types.from_name('Edm.Double')
    assert repr(typ.traits) == 'EdmFPNumTypTraits(15,d)'
    assert typ.traits.from_literal('1E+10d') == 10.0**10
    assert typ.traits.from_literal('1E+10') == 10.0**10
    assert typ.traits.from_literal('2.029d') == 2.029
    assert typ.traits.from_literal('2.0d') == 2.0
    assert typ.traits.from_json('2.0d') == 2.0
    assert typ.traits.to_literal(10.0**10) == '1.000000E+10'
    assert typ.traits.to_literal(2.029) == '2.029000E+00'
    assert typ.traits.to_literal(2.0) == '2.000000E+00'
    assert typ.traits.to_json(2.0) == '2.000000E+00'

    typ = Types.from_name('Edm.Single')
    assert repr(typ.traits) == 'EdmFPNumTypTraits(7,f)'
    assert typ.traits.from_literal('2.029f') == 2.029
    assert typ.traits.from_literal('2.029') == 2.029
    assert typ.traits.from_json('2.029f') == 2.029
    assert typ.traits.to_literal(2.029) == '2.029000'
    assert typ.traits.to_json(2.029) == '2.029000'

    typ = Types.from_name('Edm.Float')
    assert repr(typ.traits) == 'EdmFPNumTypTraits(7,d)'
    assert typ.traits.from_literal('2.029d') == 2.029
    assert typ.traits.from_literal('2.029') == 2.029
    assert typ.traits.from_json('2.029d') == 2.029
    assert typ.traits.from_json('3.76000000E+04') == 3.76*10**4
    assert typ.traits.to_literal(2.029) == '2.029000E+00'
    assert typ.traits.to_json(2.029) == '2.029000E+00'

    # GUIDs
    typ = Types.from_name('Edm.Guid')
    assert repr(typ.traits) == 'EdmPrefixedTypTraits'
    assert typ.traits.to_literal('000-0000') == "guid'000-0000'"
    assert typ.traits.from_literal("guid'1234-56'") == '1234-56'
    with pytest.raises(PyODataModelError) as e_info:
        typ.traits.from_literal("'1234-56'")
    assert str(e_info.value).startswith("Malformed value '1234-56' for primitive")


@pytest.mark.parametrize('datetime_literal,expected', [
    ('2001-02-03T04:05:06.000007', datetime(2001, 2, 3, 4, 5, 6, microsecond=7)),
    ('2001-02-03T04:05:06', datetime(2001, 2, 3, 4, 5, 6, 0)),
    ('2001-02-03T04:05', datetime(2001, 2, 3, 4, 5, 0, 0)),
])
def test_parse_datetime_literal(datetime_literal, expected):
    assert parse_datetime_literal(datetime_literal) == expected


@pytest.mark.parametrize('illegal_input', [
    '2001-02-03T04:05:61',
    '2001-02-03T04:61',
    '2001-02-03T24:05',
    '2001-02-32T04:05',
    '2001-13-03T04:05',
    '2001-00-03T04:05',
    '01-02-03T04:05',
    '2001-02-03T04:05.AAA',
    '',
])
def test_parse_datetime_literal_faulty(illegal_input):
    with pytest.raises(PyODataModelError) as e_info:
        parse_datetime_literal(f'{illegal_input}')
    assert str(e_info.value).startswith(f'Cannot decode datetime from value {illegal_input}')


def test_traits_datetime(type_date_time):
    """Test Edm.DateTime traits"""

    type_date_time = Types.from_name('Edm.DateTime')
    assert repr(type_date_time.traits) == 'EdmDateTimeTypTraits'

    # 1. direction Python -> OData

    testdate = datetime(2005, 1, 28, 18, 30, 44, 123456, tzinfo=timezone.utc)
    assert type_date_time.traits.to_literal(testdate) == "datetime'2005-01-28T18:30:44.123456'"

    # without miliseconds part
    testdate = datetime(2005, 1, 28, 18, 30, 44, 0, tzinfo=timezone.utc)
    assert type_date_time.traits.to_literal(testdate) == "datetime'2005-01-28T18:30:44'"

    # serialization of invalid value
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time.traits.to_literal('xyz')
    assert str(e_info.value).startswith('Cannot convert value of type')

    # 2. direction Literal -> python

    # parsing full representation
    testdate = type_date_time.traits.from_literal("datetime'1976-11-23T03:33:06.654321'")
    assert testdate.year == 1976
    assert testdate.month == 11
    assert testdate.day == 23
    assert testdate.hour == 3
    assert testdate.minute == 33
    assert testdate.second == 6
    assert testdate.microsecond == 654321
    assert testdate.tzinfo == timezone.utc

    # parsing without miliseconds
    testdate = type_date_time.traits.from_literal("datetime'1976-11-23T03:33:06'")
    assert testdate.year == 1976
    assert testdate.second == 6
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone.utc

    # parsing without seconds and miliseconds
    testdate = type_date_time.traits.from_literal("datetime'1976-11-23T03:33'")
    assert testdate.year == 1976
    assert testdate.minute == 33
    assert testdate.second == 0
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone.utc

    # parsing invalid value
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time.traits.from_literal('xyz')
    assert str(e_info.value).startswith('Malformed value xyz for primitive')

    with pytest.raises(PyODataModelError) as e_info:
        type_date_time.traits.from_literal("datetime'xyz'")
    assert str(e_info.value).startswith('Cannot decode datetime from value xyz')

    # 3. direction OData -> python

    # parsing full representation
    testdate = type_date_time.traits.from_json("/Date(217567986010)/")
    assert testdate.year == 1976
    assert testdate.month == 11
    assert testdate.day == 23
    assert testdate.hour == 3
    assert testdate.minute == 33
    assert testdate.second == 6
    assert testdate.microsecond == 10000
    assert testdate.tzinfo == timezone.utc

    # parsing without miliseconds
    testdate = type_date_time.traits.from_json("/Date(217567986000)/")
    assert testdate.year == 1976
    assert testdate.second == 6
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone.utc

    # parsing without seconds and miliseconds
    testdate = type_date_time.traits.from_json("/Date(217567980000)/")
    assert testdate.year == 1976
    assert testdate.minute == 33
    assert testdate.second == 0
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone.utc

    # parsing below lowest value with workaround
    pyodata.v2.model.FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE = True
    testdate = type_date_time.traits.from_json("/Date(-62135596800001)/")
    assert testdate.year == 1
    assert testdate.month == 1
    assert testdate.day == 1
    assert testdate.tzinfo == timezone.utc

    # parsing the lowest value
    pyodata.v2.model.FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE = False
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time.traits.from_json("/Date(-62135596800001)/")
    assert str(e_info.value).startswith('Cannot decode datetime from value -62135596800001.')
       
    testdate = type_date_time.traits.from_json("/Date(-62135596800000)/")
    assert testdate.year == 1
    assert testdate.month == 1
    assert testdate.day == 1
    assert testdate.hour == 0
    assert testdate.minute == 0
    assert testdate.second == 0
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone.utc

    # parsing above highest value with workaround
    pyodata.v2.model.FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE = True
    testdate = type_date_time.traits.from_json("/Date(253402300800000)/")
    assert testdate.year == 9999
    assert testdate.month == 12
    assert testdate.day == 31
    assert testdate.tzinfo == timezone.utc

    # parsing the highest value
    pyodata.v2.model.FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE = False
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time.traits.from_json("/Date(253402300800000)/")
    assert str(e_info.value).startswith('Cannot decode datetime from value 253402300800000.')

    testdate = type_date_time.traits.from_json("/Date(253402300799999)/")
    assert testdate.year == 9999
    assert testdate.month == 12
    assert testdate.day == 31
    assert testdate.hour == 23
    assert testdate.minute == 59
    assert testdate.second == 59
    assert testdate.microsecond == 999000
    assert testdate.tzinfo == timezone.utc

    # parsing invalid value
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time.traits.from_json("xyz")
    assert str(e_info.value).startswith('Malformed value xyz for primitive')

    with pytest.raises(PyODataModelError) as e_info:
        type_date_time.traits.from_json("/Date(xyz)/")
    assert str(e_info.value).startswith('Malformed value /Date(xyz)/ for primitive Edm.DateTime type.')


def test_traits_datetime_with_offset_from_json(type_date_time):
    """Test Edm.DateTime with offset"""

    # +10 hours offset, yet must be converted to UTC
    testdate = type_date_time.traits.from_json("/Date(217567986010+0600)/")
    assert testdate.year == 1976
    assert testdate.month == 11
    assert testdate.day == 23
    assert testdate.hour == 13 # 3 + 10 hours offset
    assert testdate.minute == 33
    assert testdate.second == 6
    assert testdate.microsecond == 10000
    assert testdate.tzinfo == timezone.utc


@pytest.mark.parametrize('python_datetime,expected,comment', [
    (datetime(1976, 11, 23, 3, 33, 6, microsecond=123000, tzinfo=timezone.utc), '/Date(217567986123)/', 'With milliseconds'),
    (datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone.utc), '/Date(217567986000)/', 'No milliseconds'),
    ])
def test_traits_datetime_with_offset_to_json(type_date_time, python_datetime, expected, comment):
    """Test Edm.DateTimeOffset trait: Python -> json"""

    assert type_date_time.traits.to_json(python_datetime) == expected, comment


def test_traits_datetimeoffset(type_date_time_offset):
    """Test Edm.DateTimeOffset traits"""

    assert repr(type_date_time_offset.traits) == 'EdmDateTimeOffsetTypTraits'


def test_traits_datetimeoffset_to_literal(type_date_time_offset):
    """Test Edm.DateTimeOffset trait: Python -> literal"""

    testdate = datetime(1, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    assert type_date_time_offset.traits.to_literal(testdate) == "datetimeoffset'0001-01-01T00:00:00+00:00'"

    testdate = datetime(2005, 1, 28, 18, 30, 44, 123456, tzinfo=timezone(timedelta(hours=3, minutes=40)))
    assert type_date_time_offset.traits.to_literal(testdate) == "datetimeoffset'2005-01-28T18:30:44.123456+03:40'"

    # without milliseconds part, negative offset
    testdate = datetime(2005, 1, 28, 18, 30, 44, 0, tzinfo=timezone(-timedelta(minutes=100)))
    assert type_date_time_offset.traits.to_literal(testdate) == "datetimeoffset'2005-01-28T18:30:44-01:40'"


def test_traits_invalid_datetimeoffset_to_literal(type_date_time_offset):
    # serialization of invalid value
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time_offset.traits.to_literal('xyz')
    assert str(e_info.value).startswith('Cannot convert value of type')


@pytest.mark.parametrize('python_datetime,expected,comment', [
    (datetime(1976, 11, 23, 3, 33, 6, microsecond=123000, tzinfo=timezone.utc), '/Date(217567986123+0000)/', 'UTC'),
    (datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=14))), '/Date(217567986000+0840)/', '+14 hours'),
    (datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=-12))), '/Date(217567986000-0720)/', '-12 hours'),
    ])
def test_traits_datetimeoffset_to_json(type_date_time_offset, python_datetime, expected, comment):
    """Test Edm.DateTimeOffset trait: Python -> json"""

    assert type_date_time_offset.traits.to_json(python_datetime) == expected, comment


@pytest.mark.parametrize('literal,expected,comment', [
    ("datetimeoffset'1976-11-23T03:33:06.654321+12:11'",
     datetime(1976, 11, 23, 3, 33, 6, microsecond=654321, tzinfo=timezone(timedelta(hours=12, minutes=11))),
     'Full representation'),
    ("datetimeoffset'1976-11-23T03:33:06+12:11'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=12, minutes=11))), 'No milliseconds'),
    ("datetimeoffset'1976-11-23T03:33:06-01:00'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=-1))), 'Negative offset'),
    ("datetimeoffset'1976-11-23t03:33:06-01:00'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=-1))), "lowercase 'T' is valid"),
    ("datetimeoffset'1976-11-23T03:33:06+00:00'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone.utc), '+00:00 is UTC'),
    ("datetimeoffset'1976-11-23T03:33:06-00:00'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone.utc), '-00:00 is UTC'),
    ("datetimeoffset'1976-11-23t03:33:06Z'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone.utc), 'Z is UTC'),
    ("datetimeoffset'1976-11-23t03:33:06+12:00'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=12))), 'On dateline'),
    ("datetimeoffset'1976-11-23t03:33:06-12:00'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=-12))), 'Minimum offset'),
    ("datetimeoffset'1976-11-23t03:33:06+14:00'", datetime(1976, 11, 23, 3, 33, 6, tzinfo=timezone(timedelta(hours=14))), 'Maximum offset'),
])
def test_traits_datetimeoffset_from_literal(type_date_time_offset, literal, expected, comment):
    """Test Edm.DateTimeOffset trait: literal -> Python"""

    assert expected == type_date_time_offset.traits.from_literal(literal), comment


def test_traits_datetimeoffset_from_invalid_literal(type_date_time_offset):
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time_offset.traits.from_literal('xyz')
    assert str(e_info.value).startswith('Malformed value xyz for primitive')

    with pytest.raises(PyODataModelError) as e_info:
        type_date_time_offset.traits.from_literal("datetimeoffset'xyz'")
    assert str(e_info.value).startswith('Cannot decode datetimeoffset from value xyz')


def test_traits_datetimeoffset_from_json(type_date_time_offset):
    """Test Edm.DateTimeOffset trait: OData -> Python"""

    # parsing full representation
    testdate = type_date_time_offset.traits.from_json("/Date(217567986010+0060)/")
    assert testdate.year == 1976
    assert testdate.month == 11
    assert testdate.day == 23
    assert testdate.hour == 3
    assert testdate.minute == 33
    assert testdate.second == 6
    assert testdate.microsecond == 10000
    assert testdate.tzinfo == timezone(timedelta(hours=1))

    # parsing without milliseconds, negative offset
    testdate = type_date_time_offset.traits.from_json("/Date(217567986000-0005)/")
    assert testdate.year == 1976
    assert testdate.minute == 33
    assert testdate.second == 6
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone(-timedelta(minutes=5))

    # parsing special edge case with no offset provided, defaults to UTC
    testdate = type_date_time_offset.traits.from_json("/Date(217567986000)/")
    assert testdate.year == 1976
    assert testdate.minute == 33
    assert testdate.second == 6
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone.utc

    # parsing below lowest value with workaround
    pyodata.v2.model.FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE = True
    testdate = type_date_time_offset.traits.from_json("/Date(-62135596800001+0001)/")
    assert testdate.year == 1
    assert testdate.month == 1
    assert testdate.day == 1
    assert testdate.minute == 0
    assert testdate.tzinfo == timezone(timedelta(minutes=1))

    # parsing the lowest value
    pyodata.v2.model.FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE = False
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time_offset.traits.from_json("/Date(-62135596800001+0001)/")
    assert str(e_info.value).startswith('Cannot decode datetime from value -62135596800001.')

    testdate = type_date_time_offset.traits.from_json("/Date(-62135596800000+0055)/")
    assert testdate.year == 1
    assert testdate.month == 1
    assert testdate.day == 1
    assert testdate.hour == 0
    assert testdate.minute == 0
    assert testdate.second == 0
    assert testdate.microsecond == 0
    assert testdate.tzinfo == timezone(timedelta(minutes=55))

    # parsing above highest value with workaround
    pyodata.v2.model.FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE = True
    testdate = type_date_time_offset.traits.from_json("/Date(253402300800000+0055)/")
    assert testdate.year == 9999
    assert testdate.month == 12
    assert testdate.day == 31
    assert testdate.minute == 0
    assert testdate.tzinfo == timezone(timedelta(minutes=55))

    # parsing the highest value
    pyodata.v2.model.FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE = False
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time_offset.traits.from_json("/Date(253402300800000+0055)/")
    assert str(e_info.value).startswith('Cannot decode datetime from value 253402300800000.')

    testdate = type_date_time_offset.traits.from_json("/Date(253402300799999-0001)/")
    assert testdate.year == 9999
    assert testdate.month == 12
    assert testdate.day == 31
    assert testdate.hour == 23
    assert testdate.minute == 59
    assert testdate.second == 59
    assert testdate.microsecond == 999000
    assert testdate.tzinfo == timezone(-timedelta(minutes=1))

    # parsing invalid value
    with pytest.raises(PyODataModelError) as e_info:
        type_date_time_offset.traits.from_json("xyz")
    assert str(e_info.value).startswith('Malformed value xyz for primitive')

    with pytest.raises(PyODataModelError) as e_info:
        type_date_time_offset.traits.from_json("/Date(xyz)/")
    assert str(e_info.value).startswith('Malformed value /Date(xyz)/ for primitive Edm.DateTimeOffset type.')


def test_traits_collections():
    """Test collection traits"""

    typ = Types.from_name('Collection(Edm.Int32)')
    assert typ.traits.from_json(['23', '34']) == [23, 34]

    typ = Types.from_name('Collection(Edm.String)')
    assert typ.traits.from_json(['Bob', 'Alice']) == ['Bob', 'Alice']


def test_type_parsing():
    """Test parsing of type names"""

    type_info = Types.parse_type_name('Edm.Boolean')
    assert type_info[0] is None
    assert type_info[1] == 'Edm.Boolean'
    assert not type_info[2]

    type_info = Types.parse_type_name('SomeType')
    assert type_info[0] is None
    assert type_info[1] == 'SomeType'
    assert not type_info[2]

    type_info = Types.parse_type_name('SomeNamespace.SomeType')
    assert type_info[0] == 'SomeNamespace'
    assert type_info[1] == 'SomeType'
    assert not type_info[2]

    # collections
    type_info = Types.parse_type_name('Collection(Edm.String)')
    assert type_info[0] is None
    assert type_info[1] == 'Edm.String'
    assert type_info[2]

    type_info = Types.parse_type_name('Collection(SomeType)')
    assert type_info[0] is None
    assert type_info[1] == 'SomeType'
    assert type_info[2]

    type_info = Types.parse_type_name('Collection(SomeNamespace.SomeType)')
    assert type_info[0] == 'SomeNamespace'
    assert type_info[1] == 'SomeType'
    assert type_info[2]


def test_types():
    """Test Types repository"""

    # generic
    for type_name in ['Edm.Binary', 'Edm.String', 'Edm.Int16', 'Edm.Guid']:
        typ = Types.from_name(type_name)
        assert typ.kind == Typ.Kinds.Primitive
        assert not typ.is_collection

    # Collection of primitive types
    typ = Types.from_name('Collection(Edm.String)')
    assert repr(typ) == 'Collection(Typ(Edm.String))'
    assert typ.kind is Typ.Kinds.Primitive
    assert typ.is_collection
    assert typ.name == 'Edm.String'


def test_complex_serializer(schema):
    """Test de/serializer of complex edm types"""

    # pylint: disable=redefined-outer-name

    # encode without edm type information
    with pytest.raises(PyODataException) as e_info:
        EdmStructTypeSerializer().to_literal(None, 'something')
    assert str(e_info.value).startswith('Cannot encode value something')

    # decode without edm type information
    with pytest.raises(PyODataException) as e_info:
        EdmStructTypeSerializer().from_json(None, 'something')
    assert str(e_info.value).startswith('Cannot decode value something')

    # entity without properties
    entity_type = EntityType('Box', 'Box', False)
    srl = EdmStructTypeSerializer()
    assert srl.to_literal(entity_type, 'something') == {}
    assert srl.from_json(entity_type, 'something') == {}

    # entity with properties of ODATA primitive types
    entity_type = schema.entity_type('TemperatureMeasurement')
    assert srl.to_literal(entity_type, {'ignored-key': 'ignored-value', 'Sensor': 'x'}) == {'Sensor': "'x'"}
    assert srl.from_json(entity_type, {'ignored-key': 'ignored-value', 'Sensor': "'x'"}) == {'Sensor': 'x'}


@patch('logging.Logger.warning')
def test_annot_v_l_missing_e_s(mock_warning, xml_builder_factory):
    """Test correct handling of annotations whose entity set does not exist"""

    xml_builder = xml_builder_factory()
    xml_builder.add_schema(
        'MISSING_ES',
        """
        <EntityType Name="Dict" sap:content-version="1">
         <Key><PropertyRef Name="Key"/></Key>
         <Property Name="Key" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:value-list="standard"/>
         <Property Name="Value" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:value-list="standard"/>
        </EntityType>
        <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm" Target="MISSING_ES.Dict/Value">
         <Annotation Term="com.sap.vocabularies.Common.v1.ValueList">
          <Record>
           <PropertyValue Property="Label" String="Data"/>
           <PropertyValue Property="CollectionPath" String="DataValueHelp"/>
           <PropertyValue Property="SearchSupported" Bool="true"/>
           <PropertyValue Property="Parameters">
            <Collection>
             <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterOut">
              <PropertyValue Property="LocalDataProperty" PropertyPath="Value"/>
              <PropertyValue Property="ValueListProperty" String="Data"/>
             </Record>
            </Collection>
           </PropertyValue>
          </Record>
         </Annotation>
        </Annotations>
        """
    )

    metadata = MetadataBuilder(xml_builder.serialize())

    with pytest.raises(RuntimeError) as e_info:
        metadata.build()
    assert str(e_info.value) == 'Entity Set DataValueHelp for ValueHelper(Dict/Value) does not exist'

    metadata.config.set_custom_error_policy({
        ParserError.ANNOTATION: PolicyWarning()
    })

    metadata.build()
    assert_logging_policy(mock_warning,
                          'RuntimeError',
                          'Entity Set DataValueHelp for ValueHelper(Dict/Value) does not exist'
                          )


@patch('logging.Logger.warning')
def test_annot_v_l_missing_e_t(mock_warning, xml_builder_factory):
    """Test correct handling of annotations whose target type does not exist"""

    xml_builder = xml_builder_factory()
    xml_builder.add_schema(
        'MISSING_ET',
        """
        <EntityType Name="Database" sap:content-version="1">
         <Key><PropertyRef Name="Data"/></Key>
         <Property Name="Data" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:value-list="standard"/>
        </EntityType>
        <EntityContainer Name="EXAMPLE_SRV" m:IsDefaultEntityContainer="true" sap:supported-formats="atom json xlsx">
         <EntitySet Name="DataValueHelp" EntityType="MISSING_ET.Database" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:searchable="true" sap:content-version="1"/>
        </EntityContainer>
        <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm" Target="MISSING_ET.Dict/Value">
         <Annotation Term="com.sap.vocabularies.Common.v1.ValueList">
          <Record>
           <PropertyValue Property="Label" String="Data"/>
           <PropertyValue Property="CollectionPath" String="DataValueHelp"/>
           <PropertyValue Property="SearchSupported" Bool="true"/>
           <PropertyValue Property="Parameters">
            <Collection>
             <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterOut">
              <PropertyValue Property="LocalDataProperty" PropertyPath="Value"/>
              <PropertyValue Property="ValueListProperty" String="Data"/>
             </Record>
            </Collection>
           </PropertyValue>
          </Record>
         </Annotation>
        </Annotations>
        """
    )

    metadata = MetadataBuilder(xml_builder.serialize())

    try:
        metadata.build()
        assert 'Expected' == 'RuntimeError'
    except RuntimeError as ex:
        assert str(ex) == 'Target Type Dict of ValueHelper(Dict/Value) does not exist'

    metadata.config.set_custom_error_policy({
        ParserError.ANNOTATION: PolicyWarning()
    })

    metadata.build()
    assert_logging_policy(mock_warning,
                          'RuntimeError',
                          'Target Type Dict of ValueHelper(Dict/Value) does not exist'
                          )


@patch('pyodata.v2.model.PolicyIgnore.resolve')
@patch('logging.Logger.warning')
def test_annot_v_l_trgt_inv_prop(mock_warning, mock_resolve, xml_builder_factory):
    """Test correct handling of annotations whose target property does not exist"""

    xml_builder = xml_builder_factory()
    xml_builder.add_schema(
        'MISSING_TP',
        """
        <EntityType Name="Dict" sap:content-version="1">
         <Key><PropertyRef Name="Key"/></Key>
         <Property Name="Key" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:value-list="standard"/>
         <Property Name="Value" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:value-list="standard"/>
        </EntityType>
        <EntityType Name="Database" sap:content-version="1">
         <Key><PropertyRef Name="Data"/></Key>
         <Property Name="Data" Type="Edm.String" Nullable="false" sap:unicode="false" sap:label="Key" sap:creatable="false" sap:updatable="false" sap:sortable="false" sap:value-list="standard"/>
        </EntityType>
        <EntityContainer Name="EXAMPLE_SRV" m:IsDefaultEntityContainer="true" sap:supported-formats="atom json xlsx">
         <EntitySet Name="DataValueHelp" EntityType="MISSING_TP.Database" sap:creatable="false" sap:updatable="false" sap:deletable="false" sap:searchable="true" sap:content-version="1"/>
        </EntityContainer>
        <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm" Target="MISSING_TP.Dict/NoExisting">
         <Annotation Term="com.sap.vocabularies.Common.v1.ValueList">
          <Record>
           <PropertyValue Property="Label" String="Data"/>
           <PropertyValue Property="CollectionPath" String="DataValueHelp"/>
           <PropertyValue Property="SearchSupported" Bool="true"/>
           <PropertyValue Property="Parameters">
            <Collection>
             <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterOut">
              <PropertyValue Property="LocalDataProperty" PropertyPath="Value"/>
              <PropertyValue Property="ValueListProperty" String="Data"/>
             </Record>
            </Collection>
           </PropertyValue>
          </Record>
         </Annotation>
        </Annotations>
        """
    )

    metadata = MetadataBuilder(xml_builder.serialize())

    with pytest.raises(RuntimeError) as typ_ex_info:
        metadata.build()
    assert typ_ex_info.value.args[0] == 'Target Property NoExisting of EntityType(Dict) as defined in ' \
                                        'ValueHelper(Dict/NoExisting) does not exist'

    metadata.config.set_custom_error_policy({
        ParserError.ANNOTATION: PolicyIgnore()
    })

    metadata.build()
    assert PolicyIgnore.resolve is mock_resolve
    mock_resolve.assert_called_once()

    metadata.config.set_custom_error_policy({
        ParserError.ANNOTATION: PolicyWarning()
    })

    metadata.build()

    assert_logging_policy(mock_warning,
                          'RuntimeError',
                          'Target Property NoExisting of EntityType(Dict) as defined in ValueHelper(Dict/NoExisting)'
                          ' does not exist'
                          )


def test_namespace_with_periods(xml_builder_factory):
    """Make sure Namespace can contain period"""

    xml_builder = xml_builder_factory()
    xml_builder.add_schema(
        'Several.Levels.Of.Names',
        """
        <EntityType Name="Dict" sap:content-version="1">
         <Key><PropertyRef Name="Key"/></Key>
         <Property Name="Key" Type="Edm.String" Nullable="false"/>
         <Property Name="Value" Type="Edm.String" Nullable="false"/>
        </EntityType>

        <EntityType Name="Database" sap:content-version="1">
         <Key><PropertyRef Name="Data"/></Key>
         <Property Name="Data" Type="Edm.String" Nullable="false"/>
         <NavigationProperty Name="Tables" Relationship="Several.Levels.Of.Names.DatabaseTables" ToRole="Table" FromRole="Schema"/>
        </EntityType>

        <Association Name="DatabaseTables">
          <End Type="Several.Levels.Of.Names.Dict" Role="Table" Multiplicity="*"/>
          <End Type="Several.Levels.Of.Names.Database" Role="Schema" Multiplicity="0"/>
          <ReferentialConstraint>
            <Principal Role="Schema">
              <PropertyRef Name="Data"/>
            </Principal>
            <Dependent Role="Table">
              <PropertyRef Name="Key"/>
            </Dependent>
          </ReferentialConstraint>
        </Association>

        <EntityContainer Name="EXAMPLE_SRV">
         <EntitySet Name="Schemas" EntityType="Several.Levels.Of.Names.Database"/>
         <EntitySet Name="Tables" EntityType="Several.Levels.Of.Names.Dict"/>
         <AssociationSet Name="SchemaTablesSet" Association="Several.Levels.Of.Names.DatabaseTables">
           <End Role="Table" EntitySet="Tables"/>
           <End Role="Schema" EntitySet="Schemas"/>
         </AssociationSet>
        </EntityContainer>
        """
    )

    schema = MetadataBuilder(xml_builder.serialize()).build()

    db_entity = schema.entity_type('Database')

    nav_prop = db_entity.nav_proprty('Tables')

    assert str(nav_prop) == 'NavigationTypeProperty(Tables)'

    assert str(nav_prop.to_role) == 'EndRole(Table)'
    assert str(nav_prop.to_role.entity_type) == 'EntityType(Dict)'

    association_info = nav_prop.association_info

    association_set = schema.association_set_by_association(association_info.name, association_info.namespace)

    assert association_set is not None

    end_role = association_set.end_by_role(nav_prop.to_role.role)

    assert end_role is not None


def test_edmx_entity_sets(schema):
    """Test EntitySet"""

    assert schema.entity_set('Cities').requires_filter is False
    assert schema.entity_set('CitiesWithFilter').requires_filter is True

    assert schema.entity_set('Cities').addressable is True
    assert schema.entity_set('CitiesNotAddressable').addressable is False

    cars_set = schema.entity_set('Cars')
    assert cars_set.pageable is False
    assert cars_set.countable is False
    assert cars_set.searchable is False
    assert cars_set.topable is True


def test_config_set_default_error_policy():
    """ Test configurability of policies """
    config = Config(
        custom_error_policies={
            ParserError.ANNOTATION: PolicyWarning()
        }
    )

    assert isinstance(config.err_policy(ParserError.ENTITY_TYPE), PolicyFatal)
    assert isinstance(config.err_policy(ParserError.ANNOTATION), PolicyWarning)

    config.set_default_error_policy(PolicyIgnore())

    assert isinstance(config.err_policy(ParserError.ENTITY_TYPE), PolicyIgnore)
    assert isinstance(config.err_policy(ParserError.ANNOTATION), PolicyIgnore)


def test_null_type(xml_builder_factory):
    """ Test NullType being correctly assigned to invalid types"""
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('TEST.NAMESPACE', """
        <EntityType Name="MasterProperty">
            <Property Name="Key" Type="Edm.UnknownType" />
        </EntityType>
        
        <EnumType Name="MasterEnum" UnderlyingType="Edm.String" />
        
         <ComplexType Name="MasterComplex">
                <Property Name="Width" Type="Edm.Double" />
                <Property Name="Width" Type="Edm.Double" />
        </ComplexType>
        
        <EntityType Name="MasterEntity">
            <NavigationProperty Name="ID" />
        </EntityType>
    """)

    metadata = MetadataBuilder(
        xml_builder.serialize(),
        config=Config(
            default_error_policy=PolicyIgnore()
        ))

    schema = metadata.build()

    type_info = TypeInfo(namespace=None, name='MasterProperty', is_collection=False)
    assert isinstance(schema.get_type(type_info).proprty('Key').typ, NullType)

    type_info = TypeInfo(namespace=None, name='MasterEnum', is_collection=False)
    assert isinstance(schema.get_type(type_info), NullType)

    type_info = TypeInfo(namespace=None, name='MasterComplex', is_collection=False)
    assert isinstance(schema.get_type(type_info), NullType)

    type_info = TypeInfo(namespace=None, name='MasterEntity', is_collection=False)
    assert isinstance(schema.get_type(type_info), NullType)

    with pytest.raises(PyODataModelError) as typ_ex_info:
        schema.get_type(type_info).Any
    assert typ_ex_info.value.args[0] == f'Cannot access this type. An error occurred during parsing type ' \
                          f'stated in xml({schema.get_type(type_info).name}) was not found, therefore it has been ' \
                          f'replaced with NullType.'


def test_faulty_association(xml_builder_factory):
    """ Test NullAssociation being correctly assigned to invalid associations"""
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('EXAMPLE_SRV', """
           <EntityType Name="MasterEntity">
               <Property Name="Key" Type="Edm.String" />
               <NavigationProperty Name="Followers" Relationship="EXAMPLE_SRV.Followers" FromRole="MasterRole"
                                    ToRole="FollowerRole"/>
           </EntityType>
           
           <EntityType Name="FollowerEntity">
               <Property Name="Key" Type="Edm.String" />
           </EntityType>

            <Association Name="Followers">
                <End Type="FaultyNamespace.MasterEntity" Multiplicity="1" Role="MasterRole"/>
                <End Type="FaultyNamespace.FollowerEntity" Multiplicity="*" Role="FollowerRole"/>
            </Association>
       """)

    metadata = MetadataBuilder(
        xml_builder.serialize(),
        config=Config(
            default_error_policy=PolicyIgnore()
        ))

    schema = metadata.build()
    assert schema.is_valid == False
    assert isinstance(schema.associations[0], NullAssociation)

    with pytest.raises(PyODataModelError) as typ_ex_info:
        schema.associations[0].Any
    assert typ_ex_info.value.args[0] == 'Cannot access this association. An error occurred during parsing ' \
                                        'association metadata due to that annotation has been omitted.'

def test_faulty_association_set(xml_builder_factory):
    """ Test NullAssociation being correctly assigned to invalid associations"""
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('EXAMPLE_SRV', """
        <EntityContainer Name="EXAMPLE_SRV" m:IsDefaultEntityContainer="true">
           <AssociationSet Name="toDataEntitySet" Association="EXAMPLE_SRV.toDataEntity">
                    <End EntitySet="MasterEntities" Role="FromRole_toDataEntity"/>
                    <End EntitySet="DataValueHelp" Role="ToRole_toDataEntity"/>
            </AssociationSet>
        </EntityContainer>
       """)

    metadata = MetadataBuilder(
        xml_builder.serialize(),
        config=Config(
            default_error_policy=PolicyWarning()
        ))

    schema = metadata.build()
    assert schema.is_valid == False
    assert isinstance(schema.association_set('toDataEntitySet'), NullAssociation)

    with pytest.raises(PyODataModelError) as typ_ex_info:
        schema.association_set('toDataEntitySet').Any
    assert typ_ex_info.value.args[0] == 'Cannot access this association. An error occurred during parsing ' \
                                        'association metadata due to that annotation has been omitted.'


def test_missing_association_for_navigation_property(xml_builder_factory):
    """ Test faulty aassociations on navigation property"""
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('EXAMPLE_SRV', """
           <EntityType Name="MasterEntity">
               <Property Name="Key" Type="Edm.String" />
               <NavigationProperty Name="Followers" Relationship="EXAMPLE_SRV.Followers" FromRole="MasterRole"
                                    ToRole="FollowerRole"/>
           </EntityType>
       """)

    metadata = MetadataBuilder(xml_builder.serialize())

    with pytest.raises(KeyError) as typ_ex_info:
        metadata.build()
    assert typ_ex_info.value.args[0] == 'Association Followers does not exist in namespace EXAMPLE_SRV'


def test_edmx_association_end_by_role():
    """Test the method end_by_role of the class Association"""

    end_from = EndRole(None, EndRole.MULTIPLICITY_ONE, 'From')
    end_to = EndRole(None, EndRole.MULTIPLICITY_ZERO_OR_ONE, 'To')

    association = Association('FooBar')
    association.end_roles.append(end_from)
    association.end_roles.append(end_to)

    assert association.end_by_role(end_from.role) == end_from
    assert association.end_by_role(end_to.role) == end_to

    with pytest.raises(KeyError) as typ_ex_info:
        association.end_by_role('Blah')
    assert typ_ex_info.value.args[0] == 'Association FooBar has no End with Role Blah'


def test_edmx_association_set_end_by_role():
    """Test the method end_by_role of the class AssociationSet"""

    end_from = AssociationSetEndRole('From', 'EntitySet')
    end_to = AssociationSetEndRole('To', 'EntitySet')

    association_set = AssociationSet('FooBar', 'Foo', 'EXAMPLE_SRV', [end_from, end_to])

    assert association_set.end_by_role(end_from.role) == end_from
    assert association_set.end_by_role(end_to.role) == end_to


def test_edmx_association_set_end_by_entity_set():
    """Test the method end_by_entity_set of the class AssociationSet"""

    end_from = AssociationSetEndRole('From', 'EntitySet1')
    end_to = AssociationSetEndRole('To', 'EntitySet2')

    association_set = AssociationSet('FooBar', 'Foo', 'EXAMPLE_SRV', [end_from, end_to])

    assert association_set.end_by_entity_set(end_from.entity_set_name) == end_from
    assert association_set.end_by_entity_set(end_to.entity_set_name) == end_to


def test_missing_data_service(xml_builder_factory):
    """Test correct handling of missing DataService tag in xml"""

    xml_builder = xml_builder_factory()
    xml_builder.data_services_is_enabled = False
    xml = xml_builder.serialize()

    try:
        MetadataBuilder(xml).build()
    except PyODataParserError as ex:
        assert str(ex) == 'Metadata document is missing the element DataServices'


def test_missing_schema(xml_builder_factory):
    """Test correct handling of missing Schema tag in xml"""

    xml_builder = xml_builder_factory()
    xml_builder.schema_is_enabled = False
    xml = xml_builder.serialize()

    try:
        MetadataBuilder(xml).build()
    except PyODataParserError as ex:
        assert str(ex) == 'Metadata document is missing the element Schema'


@patch.object(Schema, 'from_etree')
def test_namespace_whitelist(mock_from_etree, xml_builder_factory):
    """Test correct handling of whitelisted namespaces"""

    xml_builder = xml_builder_factory()
    xml_builder.namespaces['edmx'] = 'http://docs.oasis-open.org/odata/ns/edmx'
    xml_builder.namespaces['edm'] = 'http://docs.oasis-open.org/odata/ns/edm'
    xml_builder.add_schema('', '')
    xml = xml_builder.serialize()

    MetadataBuilder(xml).build()
    assert Schema.from_etree is mock_from_etree
    mock_from_etree.assert_called_once()


@patch.object(Schema, 'from_etree')
def test_unsupported_edmx_n(mock_from_etree, xml_builder_factory):
    """Test correct handling of non-whitelisted Edmx namespaces"""

    xml_builder = xml_builder_factory()
    edmx = 'wedonotsupportthisnamespace.com'
    xml_builder.namespaces['edmx'] = edmx
    xml_builder.add_schema('', '')
    xml = xml_builder.serialize()

    MetadataBuilder(
        xml,
        config=Config(
            xml_namespaces={'edmx': edmx}
        )
    ).build()

    assert Schema.from_etree is mock_from_etree
    mock_from_etree.assert_called_once()

    try:
        MetadataBuilder(xml).build()
    except PyODataParserError as ex:
        assert str(ex) == f'Unsupported Edmx namespace - {edmx}'

    mock_from_etree.assert_called_once()


@patch.object(Schema, 'from_etree')
def test_unsupported_schema_n(mock_from_etree, xml_builder_factory):
    """Test correct handling of non-whitelisted Schema namespaces"""

    xml_builder = xml_builder_factory()
    edm = 'wedonotsupportthisnamespace.com'
    xml_builder.namespaces['edm'] = edm
    xml_builder.add_schema('', '')
    xml = xml_builder.serialize()

    MetadataBuilder(
        xml,
        config=Config(
            xml_namespaces={'edm': edm}
        )
    ).build()

    assert Schema.from_etree is mock_from_etree
    mock_from_etree.assert_called_once()

    try:

        MetadataBuilder(xml).build()
    except PyODataParserError as ex:
        assert str(ex) == f'Unsupported Schema namespace - {edm}'

    mock_from_etree.assert_called_once()


@patch.object(Schema, 'from_etree')
def test_whitelisted_edm_namespace(mock_from_etree, xml_builder_factory):
    """Test correct handling of whitelisted Microsoft's edm namespace"""

    xml_builder = xml_builder_factory()
    xml_builder.namespaces['edm'] = 'http://schemas.microsoft.com/ado/2009/11/edm'
    xml_builder.add_schema('', '')
    xml = xml_builder.serialize()

    MetadataBuilder(xml).build()
    assert Schema.from_etree is mock_from_etree
    mock_from_etree.assert_called_once()


@patch.object(Schema, 'from_etree')
def test_whitelisted_edm_namespace_2006_04(mock_from_etree, xml_builder_factory):
    """Test correct handling of whitelisted Microsoft's edm namespace"""

    xml_builder = xml_builder_factory()
    xml_builder.namespaces['edm'] = 'http://schemas.microsoft.com/ado/2006/04/edm'
    xml_builder.add_schema('', '')
    xml = xml_builder.serialize()

    MetadataBuilder(xml).build()
    assert Schema.from_etree is mock_from_etree
    mock_from_etree.assert_called_once()


@patch.object(Schema, 'from_etree')
def test_whitelisted_edm_namespace_2007_05(mock_from_etree, xml_builder_factory):
    """Test correct handling of whitelisted Microsoft's edm namespace"""

    xml_builder = xml_builder_factory()
    xml_builder.namespaces['edm'] = 'http://schemas.microsoft.com/ado/2007/05/edm'
    xml_builder.add_schema('', '')
    xml = xml_builder.serialize()

    MetadataBuilder(xml).build()
    assert Schema.from_etree is mock_from_etree
    mock_from_etree.assert_called_once()


def test_enum_parsing(schema):
    """Test correct parsing of enum"""

    country = schema.enum_type('Country').USA
    assert str(country) == "Country'USA'"

    country2 = schema.enum_type('Country')['USA']
    assert str(country2) == "Country'USA'"

    try:
        schema.enum_type('Country').Cyprus
    except PyODataException as ex:
        assert str(ex) == f'EnumType EnumType(Country) has no member Cyprus'

    c = schema.enum_type('Country')[1]
    assert str(c) == "Country'China'"

    try:
        schema.enum_type('Country')[15]
    except PyODataException as ex:
        assert str(ex) == f'EnumType EnumType(Country) has no member with value {15}'

    type_info = TypeInfo(namespace=None, name='Country', is_collection=False)

    try:
        schema.get_type(type_info)
    except PyODataModelError as ex:
        assert str(ex) == f'Neither primitive types nor types parsed from service metadata contain requested type {type_info[0]}'

    language = schema.enum_type('Language')
    assert language.is_flags is True

    try:
        schema.enum_type('ThisEnumDoesNotExist')
    except KeyError as ex:
        assert str(ex) == f'\'EnumType ThisEnumDoesNotExist does not exist in any Schema Namespace\''

    try:
        schema.enum_type('Country', 'WrongNamespace').USA
    except KeyError as ex:
        assert str(ex) == '\'EnumType Country does not exist in Schema Namespace WrongNamespace\''


def test_unsupported_enum_underlying_type(xml_builder_factory):
    """Test if parser will parse only allowed underlying types"""
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('Test', '<EnumType Name="UnsupportedEnumType" UnderlyingType="Edm.Bool" />')
    xml = xml_builder.serialize()

    try:
        MetadataBuilder(xml).build()
    except PyODataParserError as ex:
        assert str(ex).startswith(f'Type Edm.Bool is not valid as underlying type for EnumType - must be one of')


def test_enum_value_out_of_range(xml_builder_factory):
    """Test if parser will check for values ot of range defined by underlying type"""
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('Test', """
        <EnumType Name="Num" UnderlyingType="Edm.Byte">
            <Member Name="TooBig" Value="-130" />
        </EnumType>
        """)
    xml = xml_builder.serialize()

    try:
        MetadataBuilder(xml).build()
    except PyODataParserError as ex:
        assert str(ex) == f'Value -130 is out of range for type Edm.Byte'


@patch('logging.Logger.warning')
def test_missing_property_referenced_in_annotation(mock_warning, xml_builder_factory):
    """Test that correct behavior when non existing property is referenced in annotation"""

    local_data_property = 'DataType'
    value_list_property = 'Type'

    schema = """
        <EntityType Name="MasterEntity" sap:content-version="1">
            <Property Name="Data" Type="Edm.String" sap:text="DataName"/>
            <Property Name="DataName" Type="Edm.String" />
            <Property Name="DataType" Type="Edm.String"/>
        </EntityType>
        <EntityType Name="DataEntity" sap:content-version="1" sap:value-list="true" sap:label="Data entities">
           <Property Name="Type" Type="Edm.String" Nullable="false"/>
        </EntityType>

        <EntityContainer Name="EXAMPLE_SRV" >
            <EntitySet Name="DataValueHelp" EntityType="EXAMPLE_SRV.DataEntity" />
        </EntityContainer>

        <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm" Target="EXAMPLE_SRV.MasterEntity/Data">
            <Annotation Term="com.sap.vocabularies.Common.v1.ValueList">
                    <Record>
                        <PropertyValue Property="CollectionPath" String="DataValueHelp"/>
                        <PropertyValue Property="Parameters">
                            <Collection>
                                <Record Type="com.sap.vocabularies.Common.v1.ValueListParameterDisplayOnly">
                                    <PropertyValue Property="LocalDataProperty" PropertyPath="{}"/>
                                    <PropertyValue Property="ValueListProperty" String="{}"/>
                                </Record>
                            </Collection>
                        </PropertyValue>
                    </Record>
                </Annotation>
        </Annotations>
    """

    # Test case 1. -> LocalDataProperty is faulty and ValueListProperty is valid
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('EXAMPLE_SRV', schema.format('---', value_list_property))
    xml = xml_builder.serialize()

    with pytest.raises(RuntimeError) as typ_ex_info:
        MetadataBuilder(xml).build()

    assert typ_ex_info.value.args[0] == 'ValueHelperParameter(Type) of ValueHelper(MasterEntity/Data) points to ' \
                                        'an non existing LocalDataProperty --- of EntityType(MasterEntity)'

    MetadataBuilder(xml, Config(
        default_error_policy=PolicyWarning()
    )).build()

    assert_logging_policy(mock_warning,
                          'RuntimeError',
                          'ValueHelperParameter(Type) of ValueHelper(MasterEntity/Data) points to '
                          'an non existing LocalDataProperty --- of EntityType(MasterEntity)'
                          )

    # Test case 2. -> LocalDataProperty is valid and ValueListProperty is faulty
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('EXAMPLE_SRV', schema.format(local_data_property, '---'))
    xml = xml_builder.serialize()

    with pytest.raises(RuntimeError) as typ_ex_info:
        MetadataBuilder(xml).build()

    assert typ_ex_info.value.args[0] == 'ValueHelperParameter(---) of ValueHelper(MasterEntity/Data) points to an non ' \
                                        'existing ValueListProperty --- of EntityType(DataEntity)'

    MetadataBuilder(xml, Config(
        default_error_policy=PolicyWarning()
    )).build()

    assert_logging_policy(mock_warning,
                          'RuntimeError',
                          'ValueHelperParameter(---) of ValueHelper(MasterEntity/Data) points to an non '
                          'existing ValueListProperty --- of EntityType(DataEntity)'
                          )

    # Test case 3. -> LocalDataProperty is valid and ValueListProperty is also valid
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('EXAMPLE_SRV', schema.format(local_data_property, value_list_property))
    xml = xml_builder.serialize()

    mock_warning.reset_mock()

    MetadataBuilder(xml, Config(
        default_error_policy=PolicyWarning()
    )).build()

    assert mock_warning.called is False


def test_struct_type_has_property_initial_instance():
    struct_type = StructType('Name', 'Label', False)

    assert struct_type.has_proprty('proprty') == False


def test_struct_type_has_property_no():
    struct_type = StructType('Name', 'Label', False)
    struct_type._properties['foo'] = 'ugly test hack'

    assert not struct_type.has_proprty('proprty')


def test_struct_type_has_property_yes():
    struct_type = StructType('Name', 'Label', False)
    struct_type._properties['proprty'] = 'ugly test hack'

    assert struct_type.has_proprty('proprty')

def test_invalid_xml(xml_builder_factory):
    """Test for invalid XML"""
    xml_builder = xml_builder_factory()
    xml_builder.add_schema('Test', """
        <EntityType Name="C_AssetTPType" sap:label="Asset" sap:content-version="1">
            <Property Name="IN_AssetIsResearchAndDev" Type="Edm.String" sap:label="R & D Asset" sap:quickinfo="India: R & D Asset"/>
        </EntityType>
        """)
    xml = xml_builder.serialize()

    with pytest.raises(PyODataParserError) as e_info:
        MetadataBuilder(xml).build()
    assert str(e_info.value) == 'Metadata document syntax error'
