""" Repository of build functions specific to the ODATA V4"""

# pylint: disable=missing-docstring

from pyodata.config import Config
from pyodata.exceptions import PyODataParserError
from pyodata.model.elements import ComplexType, Schema, EnumType, NullType, build_element
from pyodata.policies import ParserError


# pylint: disable=protected-access
# While building schema it is necessary to set few attributes which in the rest of the application should remain
# constant.
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

    # TODO: resolve types of properties
    # TODO: Then, process Associations nodes because they refer EntityTypes and they are referenced by AssociationSets.
    # TODO: resolve navigation properties
    # TODO: Then, process EntitySet, FunctionImport and AssociationSet nodes.
    # TODO: Finally, process Annotation nodes when all Scheme nodes are completely processed.

    return Schema
