""" Reusable implementation of from_etree methods for the most of edm elements """

# pylint: disable=unused-argument, missing-docstring, invalid-name
import logging

from pyodata.config import Config
from pyodata.exceptions import PyODataParserError, PyODataModelError
from pyodata.model.elements import sap_attribute_get_bool, sap_attribute_get_string, StructType, StructTypeProperty, \
    NavigationTypeProperty, Identifier, Types, EnumType, EnumMember, EntitySet, EndRole, ReferentialConstraint, \
    PrincipalRole, DependentRole, Association, AssociationSetEndRole, AssociationSet, \
    ValueHelper, ValueHelperParameter, FunctionImportParameter, \
    FunctionImport, metadata_attribute_get, EntityType, ComplexType, Annotation


def modlog():
    return logging.getLogger("callbacks")


def struct_type_property_from_etree(entity_type_property_node, config: Config):
    return StructTypeProperty(
        entity_type_property_node.get('Name'),
        Types.parse_type_name(entity_type_property_node.get('Type')),
        entity_type_property_node.get('Nullable'),
        entity_type_property_node.get('MaxLength'),
        entity_type_property_node.get('Precision'),
        entity_type_property_node.get('Scale'),
        # TODO: create a class SAP attributes
        sap_attribute_get_bool(entity_type_property_node, 'unicode', True),
        sap_attribute_get_string(entity_type_property_node, 'label'),
        sap_attribute_get_bool(entity_type_property_node, 'creatable', True),
        sap_attribute_get_bool(entity_type_property_node, 'updatable', True),
        sap_attribute_get_bool(entity_type_property_node, 'sortable', True),
        sap_attribute_get_bool(entity_type_property_node, 'filterable', True),
        sap_attribute_get_string(entity_type_property_node, 'filter-restriction'),
        sap_attribute_get_bool(entity_type_property_node, 'required-in-filter', False),
        sap_attribute_get_string(entity_type_property_node, 'text'),
        sap_attribute_get_bool(entity_type_property_node, 'visible', True),
        sap_attribute_get_string(entity_type_property_node, 'display-format'),
        sap_attribute_get_string(entity_type_property_node, 'value-list'), )


# pylint: disable=protected-access
def struct_type_from_etree(type_node, config: Config, kwargs):
    name = type_node.get('Name')
    label = sap_attribute_get_string(type_node, 'label')
    is_value_list = sap_attribute_get_bool(type_node, 'value-list', False)

    stype = kwargs['type'](name, label, is_value_list)

    for proprty in type_node.xpath('edm:Property', namespaces=config.namespaces):
        stp = StructTypeProperty.from_etree(proprty, config)

        if stp.name in stype._properties:
            raise KeyError('{0} already has property {1}'.format(stype, stp.name))

        stype._properties[stp.name] = stp

    # We have to update the property when
    # all properites are loaded because
    # there might be links between them.
    for ctp in list(stype._properties.values()):
        ctp.struct_type = stype

    return stype


def navigation_type_property_from_etree(node, config: Config):
    return NavigationTypeProperty(
        node.get('Name'), node.get('FromRole'), node.get('ToRole'), Identifier.parse(node.get('Relationship')))


def complex_type_from_etree(etree, config: Config):
    return StructType.from_etree(etree, config, type=ComplexType)


# pylint: disable=protected-access
def entity_type_from_etree(etree, config: Config):
    etype = StructType.from_etree(etree, config, type=EntityType)

    for proprty in etree.xpath('edm:Key/edm:PropertyRef', namespaces=config.namespaces):
        etype._key.append(etype.proprty(proprty.get('Name')))

    for proprty in etree.xpath('edm:NavigationProperty', namespaces=config.namespaces):
        navp = NavigationTypeProperty.from_etree(proprty, config)

        if navp.name in etype._nav_properties:
            raise KeyError('{0} already has navigation property {1}'.format(etype, navp.name))

        etype._nav_properties[navp.name] = navp

    return etype


# pylint: disable=protected-access, too-many-locals
def enum_type_from_etree(type_node, config: Config, kwargs):
    ename = type_node.get('Name')
    is_flags = type_node.get('IsFlags')

    namespace = kwargs['namespace']

    underlying_type = type_node.get('UnderlyingType')

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


def entity_set_from_etree(entity_set_node, config):
    name = entity_set_node.get('Name')
    et_info = Types.parse_type_name(entity_set_node.get('EntityType'))

    # TODO: create a class SAP attributes
    addressable = sap_attribute_get_bool(entity_set_node, 'addressable', True)
    creatable = sap_attribute_get_bool(entity_set_node, 'creatable', True)
    updatable = sap_attribute_get_bool(entity_set_node, 'updatable', True)
    deletable = sap_attribute_get_bool(entity_set_node, 'deletable', True)
    searchable = sap_attribute_get_bool(entity_set_node, 'searchable', False)
    countable = sap_attribute_get_bool(entity_set_node, 'countable', True)
    pageable = sap_attribute_get_bool(entity_set_node, 'pageable', True)
    topable = sap_attribute_get_bool(entity_set_node, 'topable', pageable)
    req_filter = sap_attribute_get_bool(entity_set_node, 'requires-filter', False)
    label = sap_attribute_get_string(entity_set_node, 'label')

    return EntitySet(name, et_info, addressable, creatable, updatable, deletable, searchable, countable, pageable,
                     topable, req_filter, label)


def end_role_from_etree(end_role_node, config):
    entity_type_info = Types.parse_type_name(end_role_node.get('Type'))
    multiplicity = end_role_node.get('Multiplicity')
    role = end_role_node.get('Role')

    return EndRole(entity_type_info, multiplicity, role)


def referential_constraint_from_etree(referential_constraint_node, config: Config):
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


# pylint: disable=protected-access
def association_from_etree(association_node, config: Config):
    name = association_node.get('Name')
    association = Association(name)

    for end in association_node.xpath('edm:End', namespaces=config.namespaces):
        end_role = EndRole.from_etree(end, config)
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
        referential_constraint = ReferentialConstraint.from_etree(refer[0], config)

    association._referential_constraint = referential_constraint

    return association


def association_set_end_role_from_etree(end_node, config):
    role = end_node.get('Role')
    entity_set = end_node.get('EntitySet')

    return AssociationSetEndRole(role, entity_set)


def association_set_from_etree(association_set_node, config: Config):
    end_roles = []
    name = association_set_node.get('Name')
    association = Identifier.parse(association_set_node.get('Association'))

    end_roles_list = association_set_node.xpath('edm:End', namespaces=config.namespaces)
    if len(end_roles) > 2:
        raise PyODataModelError('Association {} cannot have more than 2 end roles'.format(name))

    for end_role in end_roles_list:
        end_roles.append(AssociationSetEndRole.from_etree(end_role, config))

    return AssociationSet(name, association.name, association.namespace, end_roles)


def external_annotation_from_etree(annotations_node, config):
    target = annotations_node.get('Target')

    if annotations_node.get('Qualifier'):
        modlog().warning('Ignoring qualified Annotations of %s', target)
        return

    for annotation in annotations_node.xpath('edm:Annotation', namespaces=config.annotation_namespace):
        annot = Annotation.from_etree(target, config, annotation_node=annotation)
        if annot is None:
            continue
        yield annot


def annotation_from_etree(target, config, kwargs):
    annotation_node = kwargs['annotation_node']
    term = annotation_node.get('Term')

    if term in config.sap_annotation_value_list:
        return ValueHelper.from_etree(target, config, annotation_node=annotation_node)

    modlog().warning('Unsupported Annotation( %s )', term)
    return None


def value_helper_from_etree(target, config, kwargs):
    label = None
    collection_path = None
    search_supported = False
    params_node = None

    annotation_node = kwargs['annotation_node']
    for prop_value in annotation_node.xpath('edm:Record/edm:PropertyValue', namespaces=config.annotation_namespace):
        rprop = prop_value.get('Property')
        if rprop == 'Label':
            label = prop_value.get('String')
        elif rprop == 'CollectionPath':
            collection_path = prop_value.get('String')
        elif rprop == 'SearchSupported':
            search_supported = prop_value.get('Bool')
        elif rprop == 'Parameters':
            params_node = prop_value

    value_helper = ValueHelper(target, collection_path, label, search_supported)

    if params_node is not None:
        for prm in params_node.xpath('edm:Collection/edm:Record', namespaces=config.annotation_namespace):
            param = ValueHelperParameter.from_etree(prm, config)
            param.value_helper = value_helper
            value_helper._parameters.append(param)

    return value_helper


def value_helper_parameter_from_etree(value_help_parameter_node, config):
    typ = value_help_parameter_node.get('Type')
    direction = config.sap_value_helper_directions[typ]
    local_prop_name = None
    list_prop_name = None
    for pval in value_help_parameter_node.xpath('edm:PropertyValue', namespaces=config.annotation_namespace):
        pv_name = pval.get('Property')
        if pv_name == 'LocalDataProperty':
            local_prop_name = pval.get('PropertyPath')
        elif pv_name == 'ValueListProperty':
            list_prop_name = pval.get('String')

    return ValueHelperParameter(direction, local_prop_name, list_prop_name)


# pylint: disable=too-many-locals
def function_import_from_etree(function_import_node, config: Config):
    name = function_import_node.get('Name')
    entity_set = function_import_node.get('EntitySet')
    http_method = metadata_attribute_get(function_import_node, 'HttpMethod')

    rt_type = function_import_node.get('ReturnType')
    rt_info = None if rt_type is None else Types.parse_type_name(rt_type)
    print(name, rt_type, rt_info)

    parameters = dict()
    for param in function_import_node.xpath('edm:Parameter', namespaces=config.namespaces):
        param_name = param.get('Name')
        param_type_info = Types.parse_type_name(param.get('Type'))
        param_nullable = param.get('Nullable')
        param_max_length = param.get('MaxLength')
        param_precision = param.get('Precision')
        param_scale = param.get('Scale')
        param_mode = param.get('Mode')

        parameters[param_name] = FunctionImportParameter(param_name, param_type_info, param_nullable,
                                                         param_max_length, param_precision, param_scale, param_mode)

    return FunctionImport(name, rt_info, entity_set, parameters, http_method)
