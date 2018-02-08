"""Tests for OData Model module"""
# pylint: disable=line-too-long,too-many-locals,too-many-statements

from datetime import datetime
import pytest
from pyodata.v2.model import Edmx, Typ, StructTypeProperty, Types, EntityType, EdmStructTypeSerializer
from pyodata.exceptions import PyODataException, PyODataModelError


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
        'TemperatureMeasurement'
    }

    assert set((entity_set.name for entity_set in schema.entity_sets)) == {
        'Addresses',
        'Employees',
        'MasterEntities',
        'DataValueHelp',
        'Cities',
        'TemperatureMeasurements'
    }

    master_entity = schema.entity_type('MasterEntity')
    assert str(master_entity) == 'EntityType(MasterEntity)'
    assert master_entity.name == 'MasterEntity'
    assert master_entity.label is None
    assert not master_entity.is_value_list
    assert sorted([p.name for p in master_entity.proprties()]) == ['Data', 'DataName', 'DataType', 'Key']

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

    # EntityType from the method typ
    assert schema.typ('MasterEntity') == schema.entity_type('MasterEntity')
    assert schema.typ('MasterEntity', namespace='EXAMPLE_SRV') == schema.entity_type('MasterEntity', namespace='EXAMPLE_SRV')

    # ComplexType from the method typ
    assert schema.typ('Building') == schema.complex_type('Building')
    assert schema.typ('Building', namespace='EXAMPLE_SRV') == schema.complex_type('Building', namespace='EXAMPLE_SRV')

    # Error handling in the method typ - without namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.typ('FooBar')
    assert typ_ex_info.value.message == 'Type FooBar does not exist in Schema'

    # Error handling in the method typ - with namespace
    with pytest.raises(KeyError) as typ_ex_info:
        assert schema.typ('FooBar', namespace='EXAMPLE_SRV')
    assert typ_ex_info.value.message == 'Type FooBar does not exist in Schema Namespace EXAMPLE_SRV'


def test_edmx_associations(schema):
    """Test parsing of associations and association sets"""

    assert set((association.name for association in schema.associations)) == {'toDataEntity', 'AssociationEmployeeAddress'}

    association = schema.association('toDataEntity')
    assert str(association) == 'Association(toDataEntity)'

    from_role = association.end_role('FromRole_toDataEntity')
    assert from_role.multiplicity == '1'
    assert str(from_role.entity_type) == 'EntityType(MasterEntity)'

    to_role = association.end_role('ToRole_toDataEntity')
    assert to_role.multiplicity == '*'
    assert str(to_role.entity_type) == 'EntityType(DataEntity)'

    principal_role = association.referential_constraint.principal
    assert principal_role.name == 'FromRole_toDataEntity'
    assert principal_role.property_names == ['Key']

    dependent_role = association.referential_constraint.dependent
    assert dependent_role.name == 'ToRole_toDataEntity'
    assert dependent_role.property_names == ['Name']

    assert set((association_set.name for association_set in schema.association_sets)) == {'toDataEntitySet', 'AssociationEmployeeAddress_AssocSet'}
    association_set = schema.association_set('toDataEntitySet')
    assert str(association_set) == 'AssociationSet(toDataEntitySet)'
    assert association_set.association_type.name == 'toDataEntity'
    assert association_set.end_roles == {'DataValueHelp': 'ToRole_toDataEntity', 'MasterEntities': 'FromRole_toDataEntity'}


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

    assert set((func_import.name for func_import in schema.function_imports)) == {'get_best_measurements', 'retrieve', 'get_max', 'sum', 'sum_complex'}
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
    assert param.typ.traits.to_odata('Foo') == "'Foo'"
    assert param.typ.traits.from_odata("'Foo'") == 'Foo'

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

    assert set((complex_type.name for complex_type in schema.complex_types)) == {'Building', 'ComplexNumber', 'Rectangle'}

    complex_number = schema.complex_type('ComplexNumber')
    assert str(complex_number) == 'ComplexType(ComplexNumber)'
    assert complex_number.name == 'ComplexNumber'
    assert sorted([p.name for p in complex_number.proprties()]) == ['Imaginary', 'Real']

    real_prop = complex_number.proprty('Real')
    assert str(real_prop) == 'StructTypeProperty(Real)'
    assert str(real_prop.struct_type) == 'ComplexType(ComplexNumber)'


def test_edmx_complex_type_prop_vh(schema):
    """Check that value helpers work also for ComplexType properties"""

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
    typ = Types.from_name('Edm.Binary')
    assert repr(typ.traits) == 'TypTraits'
    assert typ.traits.to_odata('bincontent') == 'bincontent'
    assert typ.traits.from_odata('some bin content') == 'some bin content'

    # string
    typ = Types.from_name('Edm.String')
    assert repr(typ.traits) == 'EdmStringTypTraits'
    assert typ.traits.to_odata('Foo Foo') == "'Foo Foo'"
    assert typ.traits.from_odata("'Alice Bob'") == 'Alice Bob'

    # bool
    typ = Types.from_name('Edm.Boolean')
    assert repr(typ.traits) == 'EdmBooleanTypTraits'
    assert typ.traits.to_odata(True) == 'true'
    assert typ.traits.from_odata('true') is True
    assert typ.traits.to_odata(False) == 'false'
    assert typ.traits.from_odata('false') is False
    assert typ.traits.to_odata(1) == 'true'
    assert typ.traits.to_odata(0) == 'false'

    # integers
    typ = Types.from_name('Edm.Int16')
    assert repr(typ.traits) == 'EdmIntTypTraits'
    assert typ.traits.to_odata(23) == '23'
    assert typ.traits.from_odata('345') == 345

    typ = Types.from_name('Edm.Int32')
    assert repr(typ.traits) == 'EdmIntTypTraits'
    assert typ.traits.to_odata(23) == '23'
    assert typ.traits.from_odata('345') == 345

    typ = Types.from_name('Edm.Int64')
    assert repr(typ.traits) == 'EdmIntTypTraits'
    assert typ.traits.to_odata(23) == '23'
    assert typ.traits.from_odata('345') == 345

    # GUIDs
    typ = Types.from_name('Edm.Guid')
    assert repr(typ.traits) == 'EdmPrefixedTypTraits'
    assert typ.traits.to_odata('000-0000') == "guid'000-0000'"
    assert typ.traits.from_odata("guid'1234-56'") == '1234-56'
    with pytest.raises(PyODataModelError) as e_info:
        typ.traits.from_odata("'1234-56'")
    assert str(e_info.value).startswith("Malformed value '1234-56' for primitive")


def test_traits_datetime():
    """Test Edm.DateTime traits"""

    typ = Types.from_name('Edm.DateTime')
    assert repr(typ.traits) == 'EdmDateTimeTypTraits'

    # 1. direction Python -> OData

    testdate = datetime(2005, 1, 28, 18, 30, 44, 123456)
    assert typ.traits.to_odata(testdate) == "datetime'2005-01-28T18:30:44.123456'"

    # without miliseconds part
    testdate = datetime(2005, 1, 28, 18, 30, 44, 0)
    assert typ.traits.to_odata(testdate) == "datetime'2005-01-28T18:30:44'"

    # serialization of invalid value
    with pytest.raises(PyODataModelError) as e_info:
        typ.traits.to_odata('xyz')
    assert str(e_info.value).startswith('Cannot convert value of type')

    # 2. direction OData -> python

    # parsing full representation
    testdate = typ.traits.from_odata("datetime'1976-11-23T03:33:06.654321'")
    assert testdate.year == 1976
    assert testdate.month == 11
    assert testdate.day == 23
    assert testdate.hour == 3
    assert testdate.minute == 33
    assert testdate.second == 6
    assert testdate.microsecond == 654321

    # parsing without miliseconds
    testdate = typ.traits.from_odata("datetime'1976-11-23T03:33:06'")
    assert testdate.year == 1976
    assert testdate.second == 6
    assert testdate.microsecond == 0

    # parsing without seconds and miliseconds
    testdate = typ.traits.from_odata("datetime'1976-11-23T03:33'")
    assert testdate.year == 1976
    assert testdate.minute == 33
    assert testdate.second == 0
    assert testdate.microsecond == 0

    # parsing invalid value
    with pytest.raises(PyODataModelError) as e_info:
        typ.traits.from_odata('xyz')
    assert str(e_info.value).startswith('Malformed value xyz for primitive')

    with pytest.raises(PyODataModelError) as e_info:
        typ.traits.from_odata("datetime'xyz'")
    assert str(e_info.value).startswith('Cannot decode datetime from value xyz')


def test_traits_collections():
    """Test collection traits"""

    typ = Types.from_name('Collection(Edm.Int32)')
    assert typ.traits.from_odata(['23', '34']) == [23, 34]

    typ = Types.from_name('Collection(Edm.String)')
    assert typ.traits.from_odata(['Bob', 'Alice']) == ['Bob', 'Alice']


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
        EdmStructTypeSerializer().to_odata(None, 'something')
    assert str(e_info.value).startswith('Cannot encode value something')

    # decode without edm type information
    with pytest.raises(PyODataException) as e_info:
        EdmStructTypeSerializer().from_odata(None, 'something')
    assert str(e_info.value).startswith('Cannot decode value something')

    # entity without properties
    entity_type = EntityType('Box', 'Box', False)
    srl = EdmStructTypeSerializer()
    assert srl.to_odata(entity_type, 'something') == {}
    assert srl.from_odata(entity_type, 'something') == {}

    # entity with properties of ODATA primitive types
    entity_type = schema.entity_type('TemperatureMeasurement')
    assert srl.to_odata(entity_type, {'ignored-key': 'ignored-value', 'Sensor': 'x'}) == {'Sensor': "'x'"}
    assert srl.from_odata(entity_type, {'ignored-key': 'ignored-value', 'Sensor': "'x'"}) == {'Sensor': 'x'}


def test_annot_v_l_missing_e_s(metadata_builder_factory):
    """Test correct handling of annotations whose entity set does not exist"""

    builder = metadata_builder_factory()
    builder.add_schema(
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

    try:
        Edmx.parse(builder.serialize())
        assert 'Expected' == 'RuntimeError'
    except RuntimeError as ex:
        assert ex.message == 'Entity Set DataValueHelp for ValueHelper(Dict/Value) does not exist'


def test_annot_v_l_missing_e_t(metadata_builder_factory):
    """Test correct handling of annotations whose target type does not exist"""

    builder = metadata_builder_factory()
    builder.add_schema(
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

    try:
        Edmx.parse(builder.serialize())
        assert 'Expected' == 'RuntimeError'
    except RuntimeError as ex:
        assert ex.message == 'Target Type Dict of ValueHelper(Dict/Value) does not exist'


def test_annot_v_l_trgt_inv_prop(metadata_builder_factory):
    """Test correct handling of annotations whose target property does not exist"""

    builder = metadata_builder_factory()
    builder.add_schema(
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

    try:
        Edmx.parse(builder.serialize())
        assert 'Expected' == 'RuntimeError'
    except RuntimeError as ex:
        assert ex.message == 'Target Property NoExisting of EntityType(Dict) as defined in ValueHelper(Dict/NoExisting) does not exist'
