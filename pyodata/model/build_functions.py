""" Reusable implementation of build functions for the most of edm elements """

# pylint: disable=unused-argument, missing-docstring, invalid-name
import copy
import logging

from pyodata.config import Config
from pyodata.exceptions import PyODataParserError
from pyodata.model.elements import sap_attribute_get_bool, sap_attribute_get_string, StructType, StructTypeProperty, \
    Types, EntitySet, ValueHelper, ValueHelperParameter, FunctionImportParameter, \
    FunctionImport, metadata_attribute_get, EntityType, ComplexType, Annotation, build_element

from pyodata.v4 import ODataV4
import pyodata.v4.elements as v4


def modlog():
    return logging.getLogger("callbacks")


def build_struct_type_property(config: Config, entity_type_property_node):
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
def build_struct_type(config: Config, type_node, typ, schema=None):
    name = type_node.get('Name')
    base_type = type_node.get('BaseType')

    if base_type is None:
        label = sap_attribute_get_string(type_node, 'label')
        is_value_list = sap_attribute_get_bool(type_node, 'value-list', False)
        stype = typ(name, label, is_value_list)
    else:
        base_type = Types.parse_type_name(base_type)

        try:
            stype = copy.deepcopy(schema.get_type(base_type))
        except KeyError:
            raise PyODataParserError(f'BaseType \'{base_type.name}\' not found in schema')
        except AttributeError:
            raise PyODataParserError(f'\'{base_type.name}\' ')

        stype._name = name

    for proprty in type_node.xpath('edm:Property', namespaces=config.namespaces):
        stp = build_element(StructTypeProperty, config, entity_type_property_node=proprty)

        if stp.name in stype._properties:
            raise KeyError('{0} already has property {1}'.format(stype, stp.name))

        stype._properties[stp.name] = stp

    # We have to update the property when
    # all properites are loaded because
    # there might be links between them.
    for ctp in list(stype._properties.values()):
        if ctp.struct_type is None:  # TODO: Is it correct
            ctp.struct_type = stype

    return stype


def build_complex_type(config: Config, type_node, schema=None):
    return build_element(StructType, config, type_node=type_node, typ=ComplexType, schema=schema)


# pylint: disable=protected-access
def build_entity_type(config: Config, type_node, schema=None):
    etype = build_element(StructType, config, type_node=type_node, typ=EntityType, schema=schema)

    for proprty in type_node.xpath('edm:Key/edm:PropertyRef', namespaces=config.namespaces):
        etype._key.append(etype.proprty(proprty.get('Name')))

    for proprty in type_node.xpath('edm:NavigationProperty', namespaces=config.namespaces):
        navp = build_element('NavigationTypeProperty', config, node=proprty)

        if navp.name in etype._nav_properties:
            raise KeyError('{0} already has navigation property {1}'.format(etype, navp.name))

        etype._nav_properties[navp.name] = navp

    return etype


def build_entity_set(config, entity_set_node):
    name = entity_set_node.get('Name')
    et_info = Types.parse_type_name(entity_set_node.get('EntityType'))

    nav_prop_bins = []
    for nav_prop_bin in entity_set_node.xpath('edm:NavigationPropertyBinding', namespaces=config.namespaces):
        nav_prop_bins.append(build_element('NavigationPropertyBinding', config, node=nav_prop_bin, et_info=et_info))

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

    if config.odata_version == ODataV4:
        return v4.EntitySet(name, et_info, addressable, creatable, updatable, deletable, searchable, countable, pageable,
                         topable, req_filter, label, nav_prop_bins)

    return EntitySet(name, et_info, addressable, creatable, updatable, deletable, searchable, countable, pageable,
                     topable, req_filter, label)


def build_external_annotation(config, annotations_node):
    target = annotations_node.get('Target')

    if annotations_node.get('Qualifier'):
        modlog().warning('Ignoring qualified Annotations of %s', target)
        return

    for annotation in annotations_node.xpath('edm:Annotation', namespaces=config.annotation_namespace):
        annot = build_element(Annotation, config, target=target, annotation_node=annotation)
        if annot is None:
            continue
        yield annot


def build_annotation(config, target, annotation_node):
    term = annotation_node.get('Term')

    if term in config.sap_annotation_value_list:
        return build_element(ValueHelper, config, target=target, annotation_node=annotation_node)

    modlog().warning('Unsupported Annotation( %s )', term)
    return None


def build_value_helper(config, target, annotation_node):
    label = None
    collection_path = None
    search_supported = False
    params_node = None

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
            param = build_element(ValueHelperParameter, config, value_help_parameter_node=prm)
            param.value_helper = value_helper
            value_helper._parameters.append(param)

    return value_helper


def build_value_helper_parameter(config, value_help_parameter_node):
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
def build_function_import(config: Config, function_import_node):
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
