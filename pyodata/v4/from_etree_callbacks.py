# pylint: disable=missing-docstring,invalid-name,unused-argument,protected-access
from pyodata.config import Config
from pyodata.exceptions import PyODataParserError
from pyodata.model.elements import ComplexType, Schema, EnumType, NullType
from pyodata.policies import ParserError


def schema_from_etree(schema_nodes, config: Config):
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
                etype = EnumType.from_etree(enum_type, config, namespace=namespace)
            except (PyODataParserError, AttributeError) as ex:
                config.err_policy(ParserError.ENUM_TYPE).resolve(ex)
                etype = NullType(enum_type.get('Name'))

            decl.add_enum_type(etype)

        for complex_type in schema_node.xpath('edm:ComplexType', namespaces=config.namespaces):
            try:
                ctype = ComplexType.from_etree(complex_type, config, schema=schema)
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
