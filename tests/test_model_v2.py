"""Tests for OData Model module"""
# pylint: disable=line-too-long,too-many-locals,too-many-statements

import pytest

from pyodata.v2.model import Edmx, Typ, EntityTypeProperty


def test_edmx(metadata):
    """Test Edmx class"""

    schema = Edmx.parse(metadata)
    assert set(schema.namespaces) == {'EXAMPLE_SRV', 'EXAMPLE_SRV_SETS'}

    assert set((entity_type.name for entity_type in schema.entity_types)) == {'MasterEntity', 'DataEntity', 'AnnotationTest', 'TemperatureMeasurement'}
    assert set((entity_set.name for entity_set in schema.entity_sets)) == {'MasterEntities', 'DataValueHelp', 'TemperatureMeasurements'}
    assert set((func_import.name for func_import in schema.function_imports)) == {'retrieve'}

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
    assert str(master_prop_key) == 'EntityTypeProperty(Key)'
    assert str(master_prop_key.entity_type) == 'EntityType(MasterEntity)'
    assert master_prop_key.value_helper is None
    assert master_prop_key.value_list == 'standard'

    master_prop_data = master_entity.proprty('Data')
    assert master_prop_data.text_proprty.name == 'DataName'
    assert master_prop_data.visible
    assert master_prop_data.max_length == EntityTypeProperty.MAXIMUM_LENGTH

    master_prop_data_vh = master_prop_data.value_helper
    assert str(master_prop_data_vh) == 'ValueHelper(MasterEntity/Data)'
    assert str(master_prop_data_vh.proprty) == 'EntityTypeProperty(Data)'

    assert str(master_prop_data_vh.entity_set) == 'EntitySet(DataValueHelp)'
    assert str(master_prop_data_vh.entity_set.entity_type) == 'EntityType(DataEntity)'

    vh_prm_data_type = master_prop_data_vh.local_property_param('DataType')
    assert str(vh_prm_data_type) == 'ValueHelperParameter(DataType=Type)'
    assert str(vh_prm_data_type.local_property) == 'EntityTypeProperty(DataType)'
    assert str(vh_prm_data_type.list_property) == 'EntityTypeProperty(Type)'

    vh_prm_description = master_prop_data_vh.list_property_param('Description')
    assert str(vh_prm_description) == 'ValueHelperParameter(Description)'
    assert str(vh_prm_description.list_property.entity_type) == 'EntityType(DataEntity)'

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


def test_traits():
    """Test individual Traits"""

    # generic
    trait_binary = Typ.from_name('Edm.Binary')
    assert repr(trait_binary.traits) == 'TypTraits'
    assert trait_binary.traits.to_odata('bincontent') == 'bincontent'
    assert trait_binary.traits.from_odata('some bin content') == 'some bin content'

    # string
    trait_string = Typ.from_name('Edm.String')
    assert repr(trait_string.traits) == 'EdmStringTypTraits'
    assert trait_string.traits.to_odata('Foo Foo') == "'Foo Foo'"
    assert trait_string.traits.from_odata("'Alice Bob'") == 'Alice Bob'

    # integers
    trait = Typ.from_name('Edm.Int16')
    assert repr(trait.traits) == 'EdmIntTypTraits'
    assert trait.traits.to_odata(23) == '23'
    assert trait.traits.from_odata('345') == 345

    trait = Typ.from_name('Edm.Int32')
    assert repr(trait.traits) == 'EdmIntTypTraits'
    assert trait.traits.to_odata(23) == '23'
    assert trait.traits.from_odata('345') == 345

    trait = Typ.from_name('Edm.Int64')
    assert repr(trait.traits) == 'EdmIntTypTraits'
    assert trait.traits.to_odata(23) == '23'
    assert trait.traits.from_odata('345') == 345

    # GUIDs
    trait_guid = Typ.from_name('Edm.Guid')
    assert repr(trait_guid.traits) == 'EdmPrefixedTypTraits'
    assert trait_guid.traits.to_odata('000-0000') == "guid'000-0000'"
    assert trait_guid.traits.from_odata("guid'1234-56'") == '1234-56'

    with pytest.raises(RuntimeError, match=r'Malformed.*'):
        trait_guid.traits.from_odata("'1234-56'")
