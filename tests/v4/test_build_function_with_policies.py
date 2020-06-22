import pytest
from lxml import etree

from pyodata.policies import ParserError, PolicyIgnore, PolicyFatal, PolicyWarning
from pyodata.exceptions import PyODataModelError, PyODataParserError
from pyodata.model.elements import build_element, Typ, NullType
from pyodata.v4 import ODataV4
from pyodata.v4.elements import NullProperty, EnumType


class TestFaultySchema:
    def test_faulty_property_type(self, template_builder):
        faulty_entity = """ 
            <EntityType Name="OData" OpenType="true">
                <Property Name="why_it_is_so_good" Type="Joke" Nullable="false"/>
            </EntityType> """

        builder, config = template_builder(ODataV4, schema_elements=[faulty_entity])
        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()
        assert ex_info.value.args[0] == 'Neither primitive types nor types parsed ' \
                                        'from service metadata contain requested type Joke'

        config.set_custom_error_policy({ParserError.PROPERTY: PolicyIgnore()})
        assert isinstance(builder.build().entity_type('OData').proprty('why_it_is_so_good').typ, NullType)

    def test_faulty_navigation_properties(self, template_builder):
        # Test handling of faulty type
        faulty_entity = """ 
            <EntityType Name="Restaurant">
                <NavigationProperty Name="Location" Type="Position"/>
            </EntityType> """
        builder, config = template_builder(ODataV4, schema_elements=[faulty_entity])

        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()
        assert ex_info.value.args[0] == 'Neither primitive types nor types parsed ' \
                                        'from service metadata contain requested type Position'

        config.set_custom_error_policy({ParserError.NAVIGATION_PROPERTY: PolicyIgnore()})
        assert isinstance(builder.build().entity_type('Restaurant').nav_proprty('Location').typ, NullType)

        # Test handling of faulty partner
        faulty_entity = """ 
            <EntityType Name="Restaurant">
                <NavigationProperty Name="Competitors" Type="Restaurant" Partner="Joke"/>
            </EntityType> """
        builder, config = template_builder(ODataV4, schema_elements=[faulty_entity])

        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()
        assert ex_info.value.args[0] == 'No navigation property with name "Joke" found in "EntityType(Restaurant)"'

        config.set_custom_error_policy({ParserError.NAVIGATION_PROPERTY: PolicyIgnore()})
        assert isinstance(builder.build().entity_type('Restaurant').nav_proprty('Competitors').partner, NullProperty)

    def test_faulty_referential_constraints(self, template_builder):
        airport = """
            <EntityType Name="Airport">
                <Key> <PropertyRef Name="Nickname" /> </Key>
                <Property Name="Nickname" Type="Edm.String" />
            </EntityType>"""

        flight = """ 
            <EntityType Name="Flight">
                <Property Name="NameOfDestination" Type="Edm.String" />
                <NavigationProperty Name="To" Type="Airport">
                    <ReferentialConstraint Property="NameOfDestination" ReferencedProperty="Name" />
                </NavigationProperty>
            </EntityType>"""

        builder, config = template_builder(ODataV4, schema_elements=[airport, flight])
        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()

        assert ex_info.value.args[0] == 'Property Name not found on EntityType(Airport)'
        config.set_custom_error_policy({ParserError.REFERENTIAL_CONSTRAINT: PolicyIgnore()})
        assert isinstance(builder.build().entity_type('Flight').nav_proprty('To').referential_constraints[0].
                          referenced_proprty, NullProperty)
        assert isinstance(builder.build().entity_type('Flight').nav_proprty('To').referential_constraints[0].proprty,
                          NullProperty)

        flight = """ 
            <EntityType Name="Flight">
                <Property Name="NameOfDestination" Type="Edm.String" />
                <NavigationProperty Name="To" Type="Airport">
                    <ReferentialConstraint Property="Name" ReferencedProperty="Nickname" />
                </NavigationProperty>
            </EntityType>"""

        builder, config = template_builder(ODataV4, schema_elements=[airport, flight])
        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()

        assert ex_info.value.args[0] == 'Property Name not found on EntityType(Flight)'
        config.set_custom_error_policy({ParserError.REFERENTIAL_CONSTRAINT: PolicyIgnore()})
        assert isinstance(builder.build().entity_type('Flight').nav_proprty('To').referential_constraints[0].
                          referenced_proprty, NullProperty)
        assert isinstance(builder.build().entity_type('Flight').nav_proprty('To').referential_constraints[0].proprty,
                          NullProperty)

    def test_faulty_entity_set(self, template_builder, caplog):
        airport = """
            <EntityType Name="Airport">
                <Key><PropertyRef Name="Name" /></Key>
                <Property Name="Name" Type="Edm.String" Nullable="false" />
                <Property Name="Location" Type="Edm.String" Nullable="false" />
            </EntityType>"""

        airports = '<EntitySet Name="Airports" EntityType="SampleService.Models.Port" />'
        builder, config = template_builder(ODataV4, schema_elements=[airport], entity_container=[airports])
        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()

        assert ex_info.value.args[0] == 'EntityType Port does not exist in Schema Namespace SampleService.Models'
        config.set_custom_error_policy({ParserError.ENTITY_SET: PolicyWarning()})
        assert builder.build().entity_sets == []
        assert caplog.messages[-1] == '[PyODataModelError] EntityType Port does not ' \
                                      'exist in Schema Namespace SampleService.Models'

    def test_faulty_navigation_property_binding(self, template_builder, caplog):
        airport = '<EntityType Name="Airport"><Property Name="Name" Type="Edm.String" Nullable="false" /></EntityType>'
        person = '<EntityType Name="Person"><Property Name="Name" Type="Edm.String" Nullable="false" /></EntityType>'
        flight = """
            <EntityType Name="Flight">
                <NavigationProperty Name="From" Type="SampleService.Models.Airport" Nullable="false" />
            </EntityType>"""
        airports = '<EntitySet Name="Airports" EntityType="SampleService.Models.Airport" />'
        people = """
            <EntitySet Name="People" EntityType="SampleService.Models.Person">
                <NavigationPropertyBinding Path="SampleService.Models.Flight/To" Target="Airports" />
            </EntitySet>"""

        builder, config = template_builder(ODataV4, schema_elements=[person, airport, flight],
                                           entity_container=[airports, people])
        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()

        assert ex_info.value.args[0] == 'EntityType(Flight) does not contain navigation property To'
        config.set_custom_error_policy({ParserError.NAVIGATION_PROPERTY_BIDING: PolicyWarning()})
        binding = builder.build().entity_set('People').navigation_property_bindings[0]
        assert caplog.messages[-1] == '[PyODataModelError] EntityType(Flight) does not contain navigation property To'
        assert isinstance(binding.path, NullType)
        assert isinstance(binding.target, NullProperty)

        people = """
                <EntitySet Name="People" EntityType="SampleService.Models.Person">
                    <NavigationPropertyBinding Path="SampleService.Models.Flight/From" Target="Ports" />
                </EntitySet>"""

        builder, config = template_builder(ODataV4, schema_elements=[person, airport, flight],
                                           entity_container=[airports, people])
        with pytest.raises(PyODataModelError) as ex_info:
            builder.build()

        assert ex_info.value.args[0] == 'EntitySet Ports does not exist in any Schema Namespace'
        config.set_custom_error_policy({ParserError.NAVIGATION_PROPERTY_BIDING: PolicyWarning()})
        binding = builder.build().entity_set('People').navigation_property_bindings[0]
        assert caplog.messages[-1] == '[PyODataModelError] EntitySet Ports does not exist in any Schema Namespace'
        assert isinstance(binding.path, NullType)
        assert isinstance(binding.target, NullProperty)


def test_build_type_definition_faulty_data(config, caplog):
    node = etree.fromstring(
        '<TypeDefinition Name="Weight" UnderlyingType="NonBaseType"> \n'
        '  <Annotation Term="Org.OData.Measures.V1.Unit" String="Kilograms"/> \n'
        '</TypeDefinition> \n')

    with pytest.raises(PyODataModelError) as ex_info:
        build_element(Typ, config, node=node)
    assert ex_info.value.args[0] == 'Requested primitive type NonBaseType is not supported in this version of ODATA'

    config.set_custom_error_policy({ParserError.TYPE_DEFINITION: PolicyWarning()})
    assert isinstance(build_element(Typ, config, node=node), NullType)
    assert caplog.messages[-1] == '[PyODataModelError] Requested primitive type NonBaseType ' \
                                  'is not supported in this version of ODATA'


def test_build_enum_type_fault_data(config, inline_namespaces, caplog):
    node = etree.fromstring(f'<EnumType Name="Gender" UnderlyingType="Edm.Bool"/>')
    with pytest.raises(PyODataParserError) as ex_info:
        build_element(EnumType, config, type_node=node, namespace=config.namespaces)
    assert ex_info.value.args[0].startswith(
        'Type Edm.Bool is not valid as underlying type for EnumType - must be one of')

    config.set_custom_error_policy({ParserError.ENUM_TYPE: PolicyIgnore()})
    assert isinstance(build_element(EnumType, config, type_node=node, namespace=config.namespaces), NullType)

    node = etree.fromstring(f'<EnumType Name="Language" UnderlyingType="Edm.Byte" {inline_namespaces}>'
                            '   <Member Name="English" Value="-1" />'
                            '</EnumType>')

    config.set_custom_error_policy({ParserError.ENUM_TYPE: PolicyFatal()})
    with pytest.raises(PyODataParserError) as ex_info:
        build_element(EnumType, config, type_node=node, namespace=config.namespaces)
    assert ex_info.value.args[0] == 'Value -1 is out of range for type Edm.Byte'

    config.set_custom_error_policy({ParserError.ENUM_TYPE: PolicyWarning()})
    assert isinstance(build_element(EnumType, config, type_node=node, namespace=config.namespaces), NullType)
    assert caplog.messages[-1] == '[PyODataParserError] Value -1 is out of range for type Edm.Byte'
