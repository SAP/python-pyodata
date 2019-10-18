""" Repository of build functions specific to the ODATA V4"""

# pylint: disable=missing-docstring
import itertools

from pyodata.config import Config
from pyodata.exceptions import PyODataParserError, PyODataModelError
from pyodata.model.elements import ComplexType, Schema, EnumType, NullType, build_element, EntityType, Types,\
    StructTypeProperty
from pyodata.policies import ParserError
from pyodata.v4.elements import NavigationTypeProperty, NullProperty, ReferentialConstraint


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

        for enum_type in schema_node.xpath('edm:EnumType', namespaces=config.namespaces):
            try:
                etype = build_element(EnumType, config, type_node=enum_type, namespace=namespace)
            except (PyODataParserError, AttributeError) as ex:
                config.err_policy(ParserError.ENUM_TYPE).resolve(ex)
                etype = NullType(enum_type.get('Name'))

            decl.add_enum_type(etype)

        for complex_type in schema_node.xpath('edm:ComplexType', namespaces=config.namespaces):
            try:
                ctype = build_element(ComplexType, config, type_node=complex_type, schema=schema)
            except (KeyError, AttributeError) as ex:
                config.err_policy(ParserError.COMPLEX_TYPE).resolve(ex)
                ctype = NullType(complex_type.get('Name'))

            decl.add_complex_type(ctype)

        for entity_type in schema_node.xpath('edm:EntityType', namespaces=config.namespaces):
            try:
                etype = build_element(EntityType, config, type_node=entity_type, schema=schema)
            except (KeyError, AttributeError) as ex:
                config.err_policy(ParserError.ENTITY_TYPE).resolve(ex)
                etype = NullType(entity_type.get('Name'))

            decl.add_entity_type(etype)

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
            partner = None
            if nav_prop.partner_info is not None:
                # Navigation properties of nav_prop.typ
                if nav_prop.typ.is_collection:
                    nav_prop_typ_nav_properties = nav_prop.typ.item_type.nav_proprties
                else:
                    nav_prop_typ_nav_properties = nav_prop.typ.nav_proprties
                partner = next(filter(lambda x: x.name == nav_prop.partner_info.name, nav_prop_typ_nav_properties))

            try:
                for ref_con in nav_prop.referential_constraints:
                    ref_con.proprty = stype.proprty(ref_con.proprty_name)
                    ref_con.referenced_proprty = nav_prop.typ.proprty(ref_con.referenced_proprty_name)

                nav_prop.partner = partner
            except (PyODataModelError, AttributeError) as ex:
                config.err_policy(ParserError.NAVIGATION_PROPERTY).resolve(ex)
                nav_prop.partner = NullProperty(nav_prop.partner_info.name)

    # TODO: Then, process Associations nodes because they refer EntityTypes and they are referenced by AssociationSets.
    # TODO: Then, process EntitySet, FunctionImport and AssociationSet nodes.
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
