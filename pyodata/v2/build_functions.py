""" Repository of build functions specific to the ODATA V2"""

# pylint: disable=unused-argument, missing-docstring
# All methods by design of 'build_element' accept config, but no all have to use it

import itertools
import logging
from typing import List

from pyodata.config import Config
from pyodata.exceptions import PyODataModelError
from pyodata.model.elements import EntityType, ComplexType, NullType, build_element, EntitySet, FunctionImport, \
    ExternalAnnotation, Annotation, Typ, Identifier, Types
from pyodata.policies import ParserError
from pyodata.v2.elements import AssociationSetEndRole, Association, AssociationSet, NavigationTypeProperty, EndRole, \
    Schema, NullAssociation, ReferentialConstraint, PrincipalRole, DependentRole


def modlog():
    """ Logging function for debugging."""
    return logging.getLogger("v2_build_functions")


# pylint: disable=protected-access,too-many-locals, too-many-branches,too-many-statements
# While building schema it is necessary to set few attributes which in the rest of the application should remain
# constant. As for now, splitting build_schema into sub-functions would not add any benefits.
def build_schema(config: Config, schema_nodes):
    schema = Schema(config)

    # Parse Schema nodes by parts to get over the problem of not-yet known
    # entity types referenced by entity sets, function imports and
    # annotations.

    # First, process EnumType, EntityType and ComplexType nodes. They have almost no dependencies on other elements.
    for schema_node in schema_nodes:
        namespace = schema_node.get('Namespace')
        decl = Schema.Declaration(namespace)
        schema._decls[namespace] = decl

        for complex_type in schema_node.xpath('edm:ComplexType', namespaces=config.namespaces):
            try:
                ctype = build_element(ComplexType, config, type_node=complex_type)
            except (KeyError, AttributeError) as ex:
                config.err_policy(ParserError.COMPLEX_TYPE).resolve(ex)
                ctype = NullType(complex_type.get('Name'))

            decl.add_complex_type(ctype)

        for entity_type in schema_node.xpath('edm:EntityType', namespaces=config.namespaces):
            try:
                etype = build_element(EntityType, config, type_node=entity_type)
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
            assoc = build_element(Association, config, association_node=association)
            try:
                for end_role in assoc.end_roles:
                    try:
                        # search and assign entity type (it must exist)
                        if end_role.entity_type_info.namespace is None:
                            end_role.entity_type_info.namespace = namespace

                        etype = schema.entity_type(end_role.entity_type_info.name, end_role.entity_type_info.namespace)

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
            eset = build_element(EntitySet, config, entity_set_node=entity_set)
            eset.entity_type = schema.entity_type(eset.entity_type_info[1], namespace=eset.entity_type_info[0])
            decl.entity_sets[eset.name] = eset

        for function_import in schema_node.xpath('edm:EntityContainer/edm:FunctionImport',
                                                 namespaces=config.namespaces):
            efn = build_element(FunctionImport, config, function_import_node=function_import)

            # complete type information for return type and parameters
            if efn.return_type_info is not None:
                efn.return_type = schema.get_type(efn.return_type_info)
            for param in efn.parameters:
                param.typ = schema.get_type(param.type_info)
            decl.function_imports[efn.name] = efn

        for association_set in schema_node.xpath('edm:EntityContainer/edm:AssociationSet',
                                                 namespaces=config.namespaces):
            assoc_set = build_element(AssociationSet, config, association_set_node=association_set)
            try:
                try:
                    assoc_set.association_type = schema.association(assoc_set.association_type_name,
                                                                    assoc_set.association_type_namespace)
                except KeyError:
                    raise PyODataModelError(f'Association {assoc_set.association_type_name} does not exist in namespace'
                                            f' {assoc_set.association_type_namespace}')

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
            etree = build_element(ExternalAnnotation, config, annotations_node=annotation_group)
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


def build_navigation_type_property(config: Config, node):
    return NavigationTypeProperty(
        node.get('Name'), node.get('FromRole'), node.get('ToRole'), Identifier.parse(node.get('Relationship')))


def build_end_role(config: Config, end_role_node):
    entity_type_info = Types.parse_type_name(end_role_node.get('Type'))
    multiplicity = end_role_node.get('Multiplicity')
    role = end_role_node.get('Role')

    return EndRole(entity_type_info, multiplicity, role)


# pylint: disable=protected-access
def build_association(config: Config, association_node):
    name = association_node.get('Name')
    association = Association(name)

    for end in association_node.xpath('edm:End', namespaces=config.namespaces):
        end_role = build_element(EndRole, config, end_role_node=end)
        if end_role.entity_type_info is None:
            raise RuntimeError('End type is not specified in the association {}'.format(name))
        association._end_roles.append(end_role)

    if len(association._end_roles) != 2:
        raise RuntimeError('Association {} does not have two end roles'.format(name))

    refer = association_node.xpath('edm:ReferentialConstraint', namespaces=config.namespaces)
    if len(refer) > 1:
        raise RuntimeError('In association {} is defined more than one referential constraint'.format(name))

    if not refer:
        referential_constraint = None
    else:
        referential_constraint = build_element(ReferentialConstraint, config, referential_constraint_node=refer[0])

    association._referential_constraint = referential_constraint

    return association


def build_association_set_end_role(config: Config, end_node):
    role = end_node.get('Role')
    entity_set = end_node.get('EntitySet')

    return AssociationSetEndRole(role, entity_set)


def build_association_set(config: Config, association_set_node):
    end_roles: List[AssociationSetEndRole] = []
    name = association_set_node.get('Name')
    association = Identifier.parse(association_set_node.get('Association'))

    end_roles_list = association_set_node.xpath('edm:End', namespaces=config.namespaces)
    if len(end_roles) > 2:
        raise PyODataModelError('Association {} cannot have more than 2 end roles'.format(name))

    for end_role in end_roles_list:
        end_roles.append(build_element(AssociationSetEndRole, config, end_node=end_role))

    return AssociationSet(name, association.name, association.namespace, end_roles)


def build_referential_constraint(config: Config, referential_constraint_node):
    principal = referential_constraint_node.xpath('edm:Principal', namespaces=config.namespaces)
    if len(principal) != 1:
        raise RuntimeError('Referential constraint must contain exactly one principal element')

    principal_name = principal[0].get('Role')
    if principal_name is None:
        raise RuntimeError('Principal role name was not specified')

    principal_refs = []
    for property_ref in principal[0].xpath('edm:PropertyRef', namespaces=config.namespaces):
        principal_refs.append(property_ref.get('Name'))
    if not principal_refs:
        raise RuntimeError('In role {} should be at least one principal property defined'.format(principal_name))

    dependent = referential_constraint_node.xpath('edm:Dependent', namespaces=config.namespaces)
    if len(dependent) != 1:
        raise RuntimeError('Referential constraint must contain exactly one dependent element')

    dependent_name = dependent[0].get('Role')
    if dependent_name is None:
        raise RuntimeError('Dependent role name was not specified')

    dependent_refs = []
    for property_ref in dependent[0].xpath('edm:PropertyRef', namespaces=config.namespaces):
        dependent_refs.append(property_ref.get('Name'))
    if len(principal_refs) != len(dependent_refs):
        raise RuntimeError('Number of properties should be equal for the principal {} and the dependent {}'
                           .format(principal_name, dependent_name))

    return ReferentialConstraint(
        PrincipalRole(principal_name, principal_refs), DependentRole(dependent_name, dependent_refs))
