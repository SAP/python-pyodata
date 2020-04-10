""" Repository of build functions specific to the ODATA V4"""

# pylint: disable=unused-argument, missing-docstring,invalid-name
# All methods by design of 'build_element' accept config, but no all have to use it

import itertools
import copy

from pyodata.config import Config
from pyodata.exceptions import PyODataParserError, PyODataModelError
from pyodata.model.build_functions import build_entity_set
from pyodata.model.elements import ComplexType, Schema, NullType, build_element, EntityType, Types, \
    StructTypeProperty, build_annotation, Typ, Identifier
from pyodata.policies import ParserError
from pyodata.v4.elements import NavigationTypeProperty, NullProperty, ReferentialConstraint, \
    NavigationPropertyBinding, EntitySet, Unit, EnumMember, EnumType


# pylint: disable=protected-access,too-many-locals,too-many-branches,too-many-statements
# While building schema it is necessary to set few attributes which in the rest of the application should remain
# constant. As for now, splitting build_schema into sub-functions would not add any benefits.
def build_schema(config: Config, schema_nodes):
    schema = Schema(config)

    # Parse Schema nodes by parts to get over the problem of not-yet known
    # entity types referenced by entity sets, function imports and
    # annotations.

    # TODO: First, process EnumType, EntityType and ComplexType nodes.
    #  They have almost no dependencies on other elements.
    for schema_node in schema_nodes:
        namespace = schema_node.get('Namespace')
        decl = Schema.Declaration(namespace)
        schema._decls[namespace] = decl

        for type_def in schema_node.xpath('edm:TypeDefinition', namespaces=config.namespaces):
            decl.add_type_definition(build_element(Typ, config, node=type_def))

        for enum_type in schema_node.xpath('edm:EnumType', namespaces=config.namespaces):
            decl.add_enum_type(build_element(EnumType, config, type_node=enum_type, namespace=namespace))

        for complex_type in schema_node.xpath('edm:ComplexType', namespaces=config.namespaces):
            decl.add_complex_type(build_element(ComplexType, config, type_node=complex_type, schema=schema))

        for entity_type in schema_node.xpath('edm:EntityType', namespaces=config.namespaces):
            decl.add_entity_type(build_element(EntityType, config, type_node=entity_type, schema=schema))

    # resolve types of properties
    for stype in itertools.chain(schema.entity_types, schema.complex_types):
        if isinstance(stype, NullType) or stype.is_collection:
            continue

        prop: StructTypeProperty
        for prop in stype.proprties():
            try:
                prop.typ = schema.get_type(prop.type_info)
            except (PyODataModelError, AttributeError) as ex:
                config.err_policy(ParserError.PROPERTY).resolve(ex)
                prop.typ = NullType(prop.type_info.name)

        if not isinstance(stype, EntityType):
            continue

        for nav_prop in stype.nav_proprties:
            try:
                nav_prop.typ = schema.get_type(nav_prop.type_info)
            except (PyODataModelError, AttributeError) as ex:
                config.err_policy(ParserError.NAVIGATION_PROPERTY).resolve(ex)
                nav_prop.typ = NullType(nav_prop.type_info.name)

    # resolve partners and referential constraints of navigation properties after typ of navigation properties
    # are resolved
    for stype in schema.entity_types:
        if isinstance(stype, NullType) or stype.is_collection:
            continue

        for nav_prop in stype.nav_proprties:
            if nav_prop.partner_info:
                try:
                    # Navigation properties of nav_prop.typ
                    nav_properties = nav_prop.typ.item_type.nav_proprties if nav_prop.typ.is_collection \
                        else nav_prop.typ.nav_proprties
                    try:
                        nav_prop.partner = next(filter(lambda x: x.name == nav_prop.partner_info.name, nav_properties))
                    except StopIteration:
                        raise PyODataModelError(f'No navigation property with name '
                                                f'"{nav_prop.partner_info.name}" found in "{nav_prop.typ}"')
                except PyODataModelError as ex:
                    config.err_policy(ParserError.NAVIGATION_PROPERTY).resolve(ex)
                    nav_prop.partner = NullProperty(nav_prop.partner_info.name)

            for ref_con in nav_prop.referential_constraints:
                try:
                    proprty = stype.proprty(ref_con.proprty_name)
                    if nav_prop.typ.is_collection:
                        referenced_proprty = nav_prop.typ.item_type.proprty(ref_con.referenced_proprty_name)
                    else:
                        referenced_proprty = nav_prop.typ.proprty(ref_con.referenced_proprty_name)
                except PyODataModelError as ex:
                    config.err_policy(ParserError.REFERENTIAL_CONSTRAINT).resolve(ex)
                    proprty = NullProperty(ref_con.proprty_name)
                    referenced_proprty = NullProperty(ref_con.referenced_proprty_name)

                ref_con.proprty = proprty
                ref_con.referenced_proprty = referenced_proprty

    # Process entity sets
    for schema_node in schema_nodes:
        namespace = schema_node.get('Namespace')
        decl = schema._decls[namespace]

        for entity_set in schema_node.xpath('edm:EntityContainer/edm:EntitySet', namespaces=config.namespaces):
            try:
                eset = build_element(EntitySet, config, entity_set_node=entity_set)
                eset.entity_type = schema.entity_type(eset.entity_type_info[1], namespace=eset.entity_type_info[0])
                decl.entity_sets[eset.name] = eset
            except (PyODataModelError, PyODataParserError) as ex:
                config.err_policy(ParserError.ENTITY_SET).resolve(ex)

    # After all entity sets are parsed resolve the individual bindings among them and entity types
    entity_set: EntitySet
    for entity_set in schema.entity_sets:
        nav_prop_bin: NavigationPropertyBinding
        for nav_prop_bin in entity_set.navigation_property_bindings:
            try:
                identifiers = nav_prop_bin.path_info
                entity_identifier = identifiers[0] if isinstance(identifiers, list) else entity_set.entity_type_info
                entity = schema.entity_type(entity_identifier.name, namespace=entity_identifier.namespace)
                name = identifiers[-1].name if isinstance(identifiers, list) else identifiers.name
                nav_prop_bin.path = entity.nav_proprty(name)

                identifiers = nav_prop_bin.target_info
                if isinstance(identifiers, list):
                    name = identifiers[-1].name
                    namespace = identifiers[-1].namespace
                else:
                    name = identifiers.name
                    namespace = identifiers.namespace

                nav_prop_bin.target = schema.entity_set(name, namespace)
            except PyODataModelError as ex:
                config.err_policy(ParserError.NAVIGATION_PROPERTY_BIDING).resolve(ex)
                nav_prop_bin.path = NullType(nav_prop_bin.path_info[-1].name)
                nav_prop_bin.target = NullProperty(nav_prop_bin.target_info)

    # TODO: Finally, process Annotation nodes when all Scheme nodes are completely processed.
    return schema


def build_navigation_type_property(config: Config, node):
    partner = Types.parse_type_name(node.get('Partner')) if node.get('Partner') else None
    ref_cons = []

    for ref_con in node.xpath('edm:ReferentialConstraint', namespaces=config.namespaces):
        ref_cons.append(ReferentialConstraint(ref_con.get('Property'), ref_con.get('ReferencedProperty')))

    return NavigationTypeProperty(
        node.get('Name'),
        Types.parse_type_name(node.get('Type')),
        node.get('nullable'),
        partner,
        node.get('contains_target'),
        ref_cons)


def build_navigation_property_binding(config: Config, node, et_info):
    # return NavigationPropertyBinding(to_path_info(node.get('Path'), et_info), node.get('Target'))

    return NavigationPropertyBinding(Identifier.parse(node.get('Path')), Identifier.parse(node.get('Target')))


def build_unit_annotation(config: Config, target: Typ, annotation_node):
    target.annotation = Unit(f'self.{target.name}', annotation_node.get('String'))


def build_type_definition(config: Config, node):
    try:
        typ = copy.deepcopy(Types.from_name(node.get('UnderlyingType'), config))
        typ.name = node.get('Name')

        annotation_nodes = node.xpath('edm:Annotation', namespaces=config.namespaces)
        if annotation_nodes:
            annotation_node = annotation_nodes[0]
            build_annotation(annotation_node.get('Term'), config, target=typ, annotation_node=annotation_node)
    except PyODataModelError as ex:
        config.err_policy(ParserError.TYPE_DEFINITION).resolve(ex)
        typ = NullType(node.get('Name'))

    return typ


# pylint: disable=too-many-arguments
def build_entity_set_v4(config, entity_set_node, name, et_info, addressable, creatable, updatable, deletable,
                        searchable, countable, pageable, topable, req_filter, label):
    nav_prop_bins = []
    for nav_prop_bin in entity_set_node.xpath('edm:NavigationPropertyBinding', namespaces=config.namespaces):
        nav_prop_bins.append(build_element(NavigationPropertyBinding, config, node=nav_prop_bin, et_info=et_info))

    return EntitySet(name, et_info, addressable, creatable, updatable, deletable, searchable, countable, pageable,
                     topable, req_filter, label, nav_prop_bins)


def build_entity_set_with_v4_builder(config, entity_set_node):
    """Adapter inserting the V4 specific builder"""

    return build_entity_set(config, entity_set_node, builder=build_entity_set_v4)


# pylint: disable=protected-access, too-many-locals
def build_enum_type(config: Config, type_node, namespace):
    try:
        ename = type_node.get('Name')
        is_flags = type_node.get('IsFlags')

        # namespace = kwargs['namespace']

        underlying_type = type_node.get('UnderlyingType')

        # https://docs.oasis-open.org/odata/odata-csdl-json/v4.01/csprd04/odata-csdl-json-v4.01-csprd04.html#sec_EnumerationType
        if underlying_type is None:
            underlying_type = 'Edm.Int32'

        valid_types = {
            'Edm.Byte': [0, 2 ** 8 - 1],
            'Edm.Int16': [-2 ** 15, 2 ** 15 - 1],
            'Edm.Int32': [-2 ** 31, 2 ** 31 - 1],
            'Edm.Int64': [-2 ** 63, 2 ** 63 - 1],
            'Edm.SByte': [-2 ** 7, 2 ** 7 - 1]
        }

        if underlying_type not in valid_types:
            raise PyODataParserError(
                f'Type {underlying_type} is not valid as underlying type for EnumType - must be one of {valid_types}')

        mtype = Types.from_name(underlying_type, config)
        etype = EnumType(ename, is_flags, mtype, namespace)

        members = type_node.xpath('edm:Member', namespaces=config.namespaces)

        next_value = 0
        for member in members:
            name = member.get('Name')
            value = member.get('Value')

            if value is not None:
                next_value = int(value)

            vtype = valid_types[underlying_type]
            if not vtype[0] < next_value < vtype[1]:
                raise PyODataParserError(f'Value {next_value} is out of range for type {underlying_type}')

            emember = EnumMember(etype, name, next_value)
            etype._member.append(emember)

            next_value += 1

        return etype
    except (PyODataParserError, AttributeError) as ex:
        config.err_policy(ParserError.ENUM_TYPE).resolve(ex)
        return NullType(type_node.get('Name'))
