import pytest
from lxml import etree

from pyodata.model.elements import build_element, TypeInfo, Typ, ComplexType, EntityType, StructTypeProperty
from pyodata.model.type_traits import EdmIntTypTraits, EdmBooleanTypTraits
from pyodata.v4 import NavigationTypeProperty, NavigationPropertyBinding
from pyodata.v4.elements import PathInfo, Unit, EntitySet, EnumType


class TestSchema:
    def test_types(self, schema):
        assert isinstance(schema.complex_type('Location'), ComplexType)
        assert isinstance(schema.entity_type('Airport'), EntityType)
        assert isinstance(schema.enum_type('Gender'), EnumType)
        assert isinstance(schema.entity_set('People'), EntitySet)

    def test_property_type(self, schema):
        person = schema.entity_type('Person')
        assert isinstance(person.proprty('Gender'), StructTypeProperty)
        assert repr(person.proprty('Gender').typ) == 'EnumType(Gender)'
        assert repr(person.proprty('Weight').typ) == 'Typ(Weight)'
        assert repr(person.proprty('AddressInfo').typ) == 'Collection(ComplexType(Location))'

    def test_navigation_properties(self, schema):
        person = schema.entity_type('Person')
        assert person.nav_proprty('Friends').typ.is_collection is True
        assert person.nav_proprty('Friends').typ.item_type == person
        assert person.nav_proprty('Friends').partner == person.nav_proprty('Friends')

    def test_referential_constraints(self, schema):
        destination_name = schema.entity_type('Flight').nav_proprty('To').referential_constraints[0]
        assert destination_name.proprty == schema.entity_type('Flight').proprty('NameOfDestination')
        assert destination_name.referenced_proprty == schema.entity_type('Airport').proprty('Name')

    def test_entity_set(self, schema):
        person = schema.entity_type('Person')
        people = schema.entity_set('People')
        assert people.entity_type == person

    def test_navigation_property_binding(self, schema):
        person = schema.entity_type('Person')
        people = schema.entity_set('People')
        assert people.entity_type == person
        bindings = people.navigation_property_bindings

        # test bindings with simple path/target
        assert bindings[0].path == person.nav_proprty('Friends')
        assert bindings[0].target == people

        # test bindings with complex path/target
        assert bindings[1].path == schema.entity_type('Flight').nav_proprty('From')
        assert bindings[1].target == schema.entity_set('Airports')


def test_build_navigation_type_property(config, inline_namespaces):
    node = etree.fromstring(
        f'<NavigationProperty Name="Friends" Type="Collection(MySpace.Person)" Partner="Friends" {inline_namespaces}>'
        '   <ReferentialConstraint Property="FriendID" ReferencedProperty="ID" />'
        '</NavigationProperty>'
    )
    navigation_type_property = build_element(NavigationTypeProperty, config, node=node)

    assert navigation_type_property.name == 'Friends'
    assert navigation_type_property.type_info == TypeInfo('MySpace', 'Person', True)
    assert navigation_type_property.partner_info == TypeInfo(None, 'Friends', False)

    assert navigation_type_property.referential_constraints[0].proprty_name == 'FriendID'
    assert navigation_type_property.referential_constraints[0].referenced_proprty_name == 'ID'


def test_build_navigation_property_binding(config):

    et_info = TypeInfo('SampleService', 'Person', False)
    node = etree.fromstring('<NavigationPropertyBinding Path="Friends" Target="People" />')
    navigation_property_binding = build_element(NavigationPropertyBinding, config, node=node, et_info=et_info)
    assert navigation_property_binding.path_info == PathInfo('SampleService', 'Person', 'Friends')
    assert navigation_property_binding.target_info == 'People'

    node = etree.fromstring(
        '<NavigationPropertyBinding Path="SampleService.Flight/Airline" Target="Airlines" />'
    )
    navigation_property_binding = build_element(NavigationPropertyBinding, config, node=node, et_info=et_info)
    assert navigation_property_binding.path_info == PathInfo('SampleService', 'Flight', 'Airline')
    assert navigation_property_binding.target_info == 'Airlines'


def test_build_unit_annotation(config):
    # Let's think about how to test side effectsite
    pass


def test_build_type_definition(config, inline_namespaces):
    node = etree.fromstring('<TypeDefinition Name="IsHuman" UnderlyingType="Edm.Boolean" />')

    type_definition = build_element(Typ, config, node=node)
    assert type_definition.is_collection is False
    assert type_definition.kind == Typ.Kinds.Primitive
    assert type_definition.name == 'IsHuman'
    assert isinstance(type_definition.traits, EdmBooleanTypTraits)

    node = etree.fromstring(
        f'<TypeDefinition Name="Weight" UnderlyingType="Edm.Int32" {inline_namespaces}>'
        '   <Annotation Term="Org.OData.Measures.V1.Unit" String="Kilograms" />'
        '</TypeDefinition>'
    )

    type_definition = build_element(Typ, config, node=node)
    assert type_definition.kind == Typ.Kinds.Primitive
    assert type_definition.name == 'Weight'
    assert isinstance(type_definition.traits, EdmIntTypTraits)
    assert isinstance(type_definition.annotation, Unit)
    assert type_definition.annotation.unit_name == 'Kilograms'


def test_build_entity_set_with_v4_builder(config, inline_namespaces):
    entity_set_node = etree.fromstring(
        f'<EntitySet Name="People" EntityType="SampleService.Person" {inline_namespaces} >'
        '   <NavigationPropertyBinding Path="Friends" Target="People" />'
        '</EntitySet>'
    )

    entity_set = build_element(EntitySet, config, entity_set_node=entity_set_node)
    assert entity_set.name == 'People'
    assert entity_set.entity_type_info == TypeInfo('SampleService', 'Person', False)
    assert entity_set.navigation_property_bindings[0].path_info == PathInfo('SampleService', 'Person', 'Friends')


def test_build_enum_type(config, inline_namespaces):
    node = etree.fromstring(f'<EnumType Name="Gender" {inline_namespaces}>'
                            '   <Member Name="Male" Value="0" />'
                            '   <Member Name="Female" Value="1" />'
                            '</EnumType>')

    enum = build_element(EnumType, config, type_node=node, namespace=config.namespaces)
    assert enum._underlying_type.name == 'Edm.Int32'
    assert enum.Male.value == 0
    assert enum.Male.name == "Male"
    assert enum['Male'] == enum.Male
    assert enum.Female == enum[1]

    node = etree.fromstring(f'<EnumType Name="Language" UnderlyingType="Edm.Int16" IsFlags="True"> {inline_namespaces}'
                            '   <Member Name="English"/>'
                            '   <Member Name="Czech"/>'
                            '</EnumType>')
    enum = build_element(EnumType, config, type_node=node, namespace=config.namespaces)
    assert enum._underlying_type.name == 'Edm.Int16'
    assert enum.is_flags is True
