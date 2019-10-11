""" This module represents implementation of ODATA V2 """

import itertools
import logging
from typing import List

from pyodata.model.type_traits import EdmBooleanTypTraits, EdmDateTimeTypTraits, EdmPrefixedTypTraits, \
    EdmIntTypTraits, EdmLongIntTypTraits, EdmStringTypTraits
from pyodata.policies import ParserError
from pyodata.config import ODATAVersion, Config
from pyodata.exceptions import PyODataParserError, PyODataModelError

from pyodata.model.elements import StructTypeProperty, StructType, NavigationTypeProperty, ComplexType, EntityType, \
    EnumType, EntitySet, EndRole, ReferentialConstraint, Association, AssociationSetEndRole, AssociationSet, \
    ExternalAnnotation, Annotation, ValueHelper, ValueHelperParameter, FunctionImport, Schema, NullType, Typ, \
    NullAssociation

from pyodata.model.from_etree_callbacks import struct_type_property_from_etree, struct_type_from_etree, \
    navigation_type_property_from_etree, complex_type_from_etree, entity_type_from_etree, enum_type_from_etree, \
    entity_set_from_etree, end_role_from_etree, referential_constraint_from_etree, association_from_etree, \
    association_set_end_role_from_etree, association_set_from_etree, external_annotation_from_etree, \
    annotation_from_etree, value_helper_from_etree, value_helper_parameter_from_etree, function_import_from_etree


def modlog():
    """ Logging function for debugging."""
    return logging.getLogger("v2")


class ODataV2(ODATAVersion):
    """ Definition of OData V2 """

    @staticmethod
    def from_etree_callbacks():
        return {
            StructTypeProperty: struct_type_property_from_etree,
            StructType: struct_type_from_etree,
            NavigationTypeProperty: navigation_type_property_from_etree,
            ComplexType: complex_type_from_etree,
            EntityType: entity_type_from_etree,
            EnumType: enum_type_from_etree,
            EntitySet: entity_set_from_etree,
            EndRole: end_role_from_etree,
            ReferentialConstraint: referential_constraint_from_etree,
            Association: association_from_etree,
            AssociationSetEndRole: association_set_end_role_from_etree,
            AssociationSet: association_set_from_etree,
            ExternalAnnotation: external_annotation_from_etree,
            Annotation: annotation_from_etree,
            ValueHelper: value_helper_from_etree,
            ValueHelperParameter: value_helper_parameter_from_etree,
            FunctionImport: function_import_from_etree,
            Schema: ODataV2.schema_from_etree
        }

    @staticmethod
    def primitive_types() -> List[Typ]:
        return [
            Typ('Null', 'null'),
            Typ('Edm.Binary', 'binary\'\''),
            Typ('Edm.Boolean', 'false', EdmBooleanTypTraits()),
            Typ('Edm.Byte', '0'),
            Typ('Edm.DateTime', 'datetime\'2000-01-01T00:00\'', EdmDateTimeTypTraits()),
            Typ('Edm.Decimal', '0.0M'),
            Typ('Edm.Double', '0.0d'),
            Typ('Edm.Single', '0.0f'),
            Typ('Edm.Guid', 'guid\'00000000-0000-0000-0000-000000000000\'', EdmPrefixedTypTraits('guid')),
            Typ('Edm.Int16', '0', EdmIntTypTraits()),
            Typ('Edm.Int32', '0', EdmIntTypTraits()),
            Typ('Edm.Int64', '0L', EdmLongIntTypTraits()),
            Typ('Edm.SByte', '0'),
            Typ('Edm.String', '\'\'', EdmStringTypTraits()),
            Typ('Edm.Time', 'time\'PT00H00M\''),
            Typ('Edm.DateTimeOffset', 'datetimeoffset\'0000-00-00T00:00:00\'')
        ]

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements, protected-access,missing-docstring
    @staticmethod
    def schema_from_etree(schema_nodes, config: Config):
        schema = Schema(config)

        # Parse Schema nodes by parts to get over the problem of not-yet known
        # entity types referenced by entity sets, function imports and
        # annotations.

        # First, process EnumType, EntityType and ComplexType nodes. They have almost no dependencies on other elements.
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
                    ctype = ComplexType.from_etree(complex_type, config)
                except (KeyError, AttributeError) as ex:
                    config.err_policy(ParserError.COMPLEX_TYPE).resolve(ex)
                    ctype = NullType(complex_type.get('Name'))

                decl.add_complex_type(ctype)

            for entity_type in schema_node.xpath('edm:EntityType', namespaces=config.namespaces):
                try:
                    etype = EntityType.from_etree(entity_type, config)
                except (KeyError, AttributeError) as ex:
                    config.err_policy(ParserError.ENTITY_TYPE).resolve(ex)
                    etype = NullType(entity_type.get('Name'))

                decl.add_entity_type(etype)

        # resolve types of properties
        for stype in itertools.chain(schema.entity_types, schema.complex_types):
            if isinstance(stype, NullType):
                continue

            if stype.kind == Typ.Kinds.Complex:
                # skip collections (no need to assign any types since type of collection
                # items is resolved separately
                if stype.is_collection:
                    continue

                for prop in stype.proprties():
                    try:
                        prop.typ = schema.get_type(prop.type_info)
                    except PyODataModelError as ex:
                        config.err_policy(ParserError.PROPERTY).resolve(ex)
                        prop.typ = NullType(prop.type_info.name)

        # pylint: disable=too-many-nested-blocks
        # Then, process Associations nodes because they refer EntityTypes and
        # they are referenced by AssociationSets.
        for schema_node in schema_nodes:
            namespace = schema_node.get('Namespace')
            decl = schema._decls[namespace]

            for association in schema_node.xpath('edm:Association', namespaces=config.namespaces):
                assoc = Association.from_etree(association, config)
                try:
                    for end_role in assoc.end_roles:
                        try:
                            # search and assign entity type (it must exist)
                            if end_role.entity_type_info.namespace is None:
                                end_role.entity_type_info.namespace = namespace

                            etype = schema.entity_type(end_role.entity_type_info.name,
                                                       end_role.entity_type_info.namespace)

                            end_role.entity_type = etype
                        except KeyError:
                            raise PyODataModelError(
                                f'EntityType {end_role.entity_type_info.name} does not exist in Schema '
                                f'Namespace {end_role.entity_type_info.namespace}')

                    if assoc.referential_constraint is not None:
                        role_names = [end_role.role for end_role in assoc.end_roles]
                        principal_role = assoc.referential_constraint.principal

                        # Check if the role was defined in the current association
                        if principal_role.name not in role_names:
                            raise RuntimeError(
                                'Role {} was not defined in association {}'.format(principal_role.name, assoc.name))

                        # Check if principal role properties exist
                        role_name = principal_role.name
                        entity_type_name = assoc.end_by_role(role_name).entity_type_name
                        schema.check_role_property_names(principal_role, entity_type_name, namespace)

                        dependent_role = assoc.referential_constraint.dependent

                        # Check if the role was defined in the current association
                        if dependent_role.name not in role_names:
                            raise RuntimeError(
                                'Role {} was not defined in association {}'.format(dependent_role.name, assoc.name))

                        # Check if dependent role properties exist
                        role_name = dependent_role.name
                        entity_type_name = assoc.end_by_role(role_name).entity_type_name
                        schema.check_role_property_names(dependent_role, entity_type_name, namespace)
                except (PyODataModelError, RuntimeError) as ex:
                    config.err_policy(ParserError.ASSOCIATION).resolve(ex)
                    decl.associations[assoc.name] = NullAssociation(assoc.name)
                else:
                    decl.associations[assoc.name] = assoc

        # resolve navigation properties
        for stype in schema.entity_types:
            # skip null type
            if isinstance(stype, NullType):
                continue

            # skip collections
            if stype.is_collection:
                continue

            for nav_prop in stype.nav_proprties:
                try:
                    assoc = schema.association(nav_prop.association_info.name, nav_prop.association_info.namespace)
                    nav_prop.association = assoc
                except KeyError as ex:
                    config.err_policy(ParserError.ASSOCIATION).resolve(ex)
                    nav_prop.association = NullAssociation(nav_prop.association_info.name)

        # Then, process EntitySet, FunctionImport and AssociationSet nodes.
        for schema_node in schema_nodes:
            namespace = schema_node.get('Namespace')
            decl = schema._decls[namespace]

            for entity_set in schema_node.xpath('edm:EntityContainer/edm:EntitySet', namespaces=config.namespaces):
                eset = EntitySet.from_etree(entity_set, config)
                eset.entity_type = schema.entity_type(eset.entity_type_info[1], namespace=eset.entity_type_info[0])
                decl.entity_sets[eset.name] = eset

            for function_import in schema_node.xpath('edm:EntityContainer/edm:FunctionImport',
                                                     namespaces=config.namespaces):
                efn = FunctionImport.from_etree(function_import, config)

                # complete type information for return type and parameters
                if efn.return_type_info is not None:
                    efn.return_type = schema.get_type(efn.return_type_info)
                for param in efn.parameters:
                    param.typ = schema.get_type(param.type_info)
                decl.function_imports[efn.name] = efn

            for association_set in schema_node.xpath('edm:EntityContainer/edm:AssociationSet',
                                                     namespaces=config.namespaces):
                assoc_set = AssociationSet.from_etree(association_set, config)
                try:
                    try:
                        assoc_set.association_type = schema.association(assoc_set.association_type_name,
                                                                        assoc_set.association_type_namespace)
                    except KeyError:
                        raise PyODataModelError(
                            'Association {} does not exist in namespace {}'
                            .format(assoc_set.association_type_name, assoc_set.association_type_namespace))

                    for end in assoc_set.end_roles:
                        # Check if an entity set exists in the current scheme
                        # and add a reference to the corresponding entity set
                        try:
                            entity_set = schema.entity_set(end.entity_set_name, namespace)
                            end.entity_set = entity_set
                        except KeyError:
                            raise PyODataModelError('EntitySet {} does not exist in Schema Namespace {}'
                                                    .format(end.entity_set_name, namespace))
                        # Check if role is defined in Association
                        if assoc_set.association_type.end_by_role(end.role) is None:
                            raise PyODataModelError('Role {} is not defined in association {}'
                                                    .format(end.role, assoc_set.association_type_name))
                except (PyODataModelError, KeyError) as ex:
                    config.err_policy(ParserError.ASSOCIATION).resolve(ex)
                    decl.association_sets[assoc_set.name] = NullAssociation(assoc_set.name)
                else:
                    decl.association_sets[assoc_set.name] = assoc_set

        # pylint: disable=too-many-nested-blocks
        # Finally, process Annotation nodes when all Scheme nodes are completely processed.
        for schema_node in schema_nodes:
            for annotation_group in schema_node.xpath('edm:Annotations', namespaces=config.annotation_namespace):
                etree = ExternalAnnotation.from_etree(annotation_group, config)
                for annotation in etree:
                    if not annotation.element_namespace != schema.namespaces:
                        modlog().warning('%s not in the namespaces %s', annotation, ','.join(schema.namespaces))
                        continue

                    try:
                        if annotation.kind == Annotation.Kinds.ValueHelper:
                            try:
                                annotation.entity_set = schema.entity_set(
                                    annotation.collection_path, namespace=annotation.element_namespace)
                            except KeyError:
                                raise RuntimeError(f'Entity Set {annotation.collection_path} '
                                                   f'for {annotation} does not exist')

                            try:
                                vh_type = schema.typ(annotation.proprty_entity_type_name,
                                                     namespace=annotation.element_namespace)
                            except KeyError:
                                raise RuntimeError(f'Target Type {annotation.proprty_entity_type_name} '
                                                   f'of {annotation} does not exist')

                            try:
                                target_proprty = vh_type.proprty(annotation.proprty_name)
                            except KeyError:
                                raise RuntimeError(f'Target Property {annotation.proprty_name} '
                                                   f'of {vh_type} as defined in {annotation} does not exist')
                        annotation.proprty = target_proprty
                        target_proprty.value_helper = annotation
                    except (RuntimeError, PyODataModelError) as ex:
                        config.err_policy(ParserError.ANNOTATION).resolve(ex)
        return schema
