"""
Simple stupid representation of Metadata of OData V2

Author: Jakub Filak <jakub.filak@sap.com>
Date:   2017-08-21
"""
# pylint: disable=missing-docstring,too-many-instance-attributes,too-many-arguments,protected-access,no-member,line-too-long,logging-format-interpolation,too-few-public-methods,too-many-lines

import StringIO
import logging
import enum
import re
from lxml import etree


class Identifier(object):

    def __init__(self, name):
        super(Identifier, self).__init__()

        self._name = name

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name


class TypTraits(object):
    """Encapsulated differences between types"""

    def __repr__(self):
        return self.__class__.__name__

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return value

    # pylint: disable=no-self-use
    def from_odatat(self, value):
        return value


class EdmPrefixedTypTraits(TypTraits):
    """Is good for all types where values have form: prefix'value'"""

    def __init__(self, prefix):
        super(EdmPrefixedTypTraits, self).__init__()
        self._prefix = prefix

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return '{}\'{}\''.format(self._prefix, value)

    # pylint: disable=no-self-use
    def from_odata(self, value):
        matches = re.match("^{}'(.*)'$".format(self._prefix), value)
        if not matches:
            raise RuntimeError('Malformed Edm.Guid {0} '.format(value))
        return matches.group(1)


class EdmStringTypTraits(TypTraits):
    """Edm.String traits"""

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return '\'%s\'' % (value)

    # pylint: disable=no-self-use
    def from_odata(self, value):
        return value.strip('\'')


class Typ(object):

    Types = None

    def __init__(self, name, null_value, traits=TypTraits()):
        super(Typ, self).__init__()

        self._name = name
        self._null_value = null_value

        self._traits = traits

    def __str__(self):
        return self._name

    @property
    def name(self):
        return self._name

    @property
    def null_value(self):
        return self._null_value

    @property
    def traits(self):
        return self._traits

    @staticmethod
    def from_name(name):
        if Typ.Types is None:
            Typ.Types = {
                'Null': Typ('Null', 'null'),
                'Edm.Binary': Typ('Edm.Binary', 'binary\'\''),
                'Edm.Boolean': Typ('Edm.Boolean', 'false'),
                'Edm.Byte': Typ('Edm.Byte', '0'),
                'Edm.DateTime': Typ('Edm.DateTime', 'datetime\'2000-01-01T00:00\''),
                'Edm.Decimal': Typ('Edm.Decimal', '0.0M'),
                'Edm.Double': Typ('Edm.Double', '0.0d'),
                'Edm.Single': Typ('Edm.Single', '0.0f'),
                'Edm.Guid': Typ('Edm.Guid',
                                'guid\'00000000-0000-0000-0000-000000000000\'', EdmPrefixedTypTraits('guid')),
                'Edm.Int16': Typ('Edm.Int16', '0'),
                'Edm.Int32': Typ('Edm.Int32', '0'),
                'Edm.Int64': Typ('Edm.Int64', '0L'),
                'Edm.SByte': Typ('Edm.SByte', '0'),
                'Edm.String': Typ('Edm.String', '\'\'', EdmStringTypTraits()),
                'Edm.Time': Typ('Edm.Time', 'time\'PT00H00M\''),
                'Edm.DateTimeOffset': Typ('Edm.DateTimeOffset',
                                          'datetimeoffset\'0000-00-00T00:00:00\''),
            }

        return Typ.Types[name]


class VariableDeclaration(Identifier):

    def __init__(self, name, typ, nullable, max_length, precision):
        super(VariableDeclaration, self).__init__(name)

        self._typ = Typ.from_name(typ)

        self._nullable = bool(nullable)
        self._max_length = int(max_length if max_length is not None else 0)
        self._precision = precision

    @property
    def typ(self):
        return self._typ

    @property
    def nullable(self):
        return self._nullable

    @property
    def max_length(self):
        return self._max_length

    @property
    def precision(self):
        return self._precision


class Schema(object):

    def __init__(self, namespace):
        super(Schema, self).__init__()

        self._namespace = namespace
        self._entity_types = dict()
        self._entity_sets = dict()
        self._function_imports = dict()

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self._namespace)

    @property
    def namespace(self):
        return self._namespace

    def entity_type(self, type_name):
        return self._entity_types[type_name]

    def entity_set(self, set_name):
        return self._entity_sets[set_name]

    @property
    def entity_sets(self):
        return self._entity_sets.values()

    def function_import(self, function_import):
        return self._function_imports[function_import]

    @staticmethod
    def from_etree(schema_node):
        namespace = schema_node.get('Namespace')
        schema = Schema(namespace)

        for entity_type in schema_node.xpath('edm:EntityType',
                                             namespaces=NAMESPACES):
            etype = EntityType.from_etree(entity_type)
            schema._entity_types[etype.name] = etype

        for entity_set in schema_node.xpath('edm:EntityContainer/edm:EntitySet',
                                            namespaces=NAMESPACES):
            eset = EntitySet.from_etree(entity_set)

            if eset.namespace != namespace:
                logging.warn('{0} not in the namespace {1}'
                             .format(eset, namespace))
                continue

            eset.entity_type = schema.entity_type(eset.entity_type_name)
            schema._entity_sets[eset.name] = eset

        for function_import in schema_node.xpath('edm:EntityContainer/edm:FunctionImport',
                                                 namespaces=NAMESPACES):
            efn = FunctionImport.from_etree(function_import)
            schema._function_imports[efn.name] = efn

        for annotation_group in schema_node.xpath('edm:Annotations',
                                                  namespaces=ANNOTATION_NAMESPACES):
            for annotation in ExternalAnnontation.from_etree(annotation_group):
                if annotation.namespace != schema.namespace:
                    logging.warn('{0} not in the namespace {1}'
                                 .format(annotation, namespace))
                    continue

                if annotation.kind == Annotation.Kinds.ValueHelper:

                    try:
                        annotation.entity_set = schema.entity_set(
                            annotation.collection_path)
                    except KeyError as ex:
                        raise RuntimeError('Entity Set {0} for {1} does not exist'
                                           .format(annotation.collection_path, annotation))

                    try:
                        vh_entity_type = schema.entity_type(
                            annotation.proprty_entity_type_name)
                    except KeyError as ex:
                        raise RuntimeError('Target Entity Type {0} of {1} does not exist'.format(annotation.propty_entity_type_name, ex.message))

                    try:
                        target_proprty = vh_entity_type.proprty(annotation.proprty_name)
                    except KeyError as ex:
                        raise RuntimeError('Target Property {0} of {1} as defined in {2} does not exist'.format(annotation.propty_name, vh_entity_type, ex.message))

                    annotation.proprty = target_proprty
                    target_proprty.value_helper = annotation

        return schema


class EntityType(object):

    def __init__(self, name, label, is_value_list):
        super(EntityType, self).__init__()

        self._name = name
        self._label = label
        self._is_value_list = is_value_list

        self._key = list()
        self._properties = dict()

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name

    @property
    def label(self):
        return self._label

    @property
    def is_value_list(self):
        return self._is_value_list

    def proprty(self, property_name):
        return self._properties[property_name]

    def proprties(self):
        return self._properties.values()

    @property
    def key_proprties(self):
        return list(self._key)

    @staticmethod
    def from_etree(entity_type_node):
        name = entity_type_node.get('Name')
        label = sap_attribute_get_string(entity_type_node, 'label')
        is_value_list = sap_attribute_get_bool(entity_type_node,
                                               'value-list', False)

        etype = EntityType(name, label, is_value_list)
        for proprty in entity_type_node.xpath('edm:Property',
                                              namespaces=NAMESPACES):
            etp = EntityTypeProperty.from_etree(proprty)

            if etp.name in etype._properties:
                raise KeyError('{0} already has property {1}'
                               .format(etp, etp.name))

            etype._properties[etp.name] = etp

        for proprty in entity_type_node.xpath('edm:Key/edm:PropertyRef',
                                              namespaces=NAMESPACES):
            etype._key.append(etype.proprty(proprty.get('Name')))

        # We have to update the property when
        # all properites are loaded because
        # there might be links between them.
        for etp in etype._properties.values():
            etp.entity_type = etype

        return etype


class EntitySet(object):

    def __init__(self, name, namespace, entity_type_name, creatable, updatable,
                 deletable, searchable):
        super(EntitySet, self).__init__()

        self._name = name
        self._namespace = namespace
        self._entity_type = None
        self._entity_type_name = entity_type_name
        self._creatable = creatable
        self._updatable = updatable
        self._deletable = deletable
        self._searchable = searchable

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace

    @property
    def entity_type_name(self):
        return self._entity_type_name

    @property
    def entity_type(self):
        return self._entity_type

    @entity_type.setter
    def entity_type(self, value):
        if self._entity_type is not None:
            raise RuntimeError('Cannot replace {0} of {1} to {2}'
                               .format(self._entity_type, self, value))

        if value.name != self.entity_type_name:
            raise RuntimeError('{0} cannot be the type of {1}'
                               .format(value, self))

        self._entity_type = value

    @property
    def creatable(self):
        return self._creatable

    @property
    def updatable(self):
        return self._updatable

    @property
    def deletable(self):
        return self._deletable

    @property
    def searchable(self):
        return self._searchable

    @staticmethod
    def from_etree(entity_set_node):
        name = entity_set_node.get('Name')
        et_ns, et_name = entity_set_node.get('EntityType').split('.')

        # TODO: create a class SAP attributes
        creatable = sap_attribute_get_bool(entity_set_node,
                                           'creatable', True)
        updatable = sap_attribute_get_bool(entity_set_node,
                                           'updatable', True)
        deletable = sap_attribute_get_bool(entity_set_node,
                                           'deletable', True)
        searchable = sap_attribute_get_bool(entity_set_node,
                                            'searchable', True)

        return EntitySet(name, et_ns, et_name, creatable,
                         updatable, deletable, searchable)


class EntityTypeProperty(VariableDeclaration):

    def __init__(self, name, typ, nullable, max_length, precision, uncode,
                 label, creatable, updatable, sortable, filterable, text,
                 visible, display_format):
        super(EntityTypeProperty, self).__init__(name, typ, nullable,
                                                 max_length, precision)

        self._value_helper = None
        self._entity_type = None
        self._uncode = uncode
        self._label = label
        self._creatable = creatable
        self._updatable = updatable
        self._sortable = sortable
        self._filterable = filterable
        self._text_proprty_name = text
        self._visible = visible
        self._display_format = display_format

        # Lazy loading
        self._text_proprty = None

    @property
    def entity_type(self):
        return self._entity_type

    @entity_type.setter
    def entity_type(self, value):
        if self._entity_type is not None:
            raise RuntimeError('Cannot replace {0} of {1} to {2}'
                               .format(self._entity_type, self, value))

        self._entity_type = value

        if self._text_proprty_name is not None:
            try:
                self._text_proprty = self._entity_type.proprty(self._text_proprty_name)
            except KeyError:
                # TODO: resolve EntityType of text property
                if '/' not in self._text_proprty_name:
                    raise RuntimeError('The attribute sap:text of {1} is set to non existing Property \'{0}\''
                                       .format(self._text_proprty_name, self))

    @property
    def text_proprty_name(self):
        return self._text_proprty_name

    @property
    def text_proprty(self):
        return self._text_proprty

    @property
    def uncode(self):
        return self._uncode

    @property
    def label(self):
        return self._label

    @property
    def creatable(self):
        return self._creatable

    @property
    def updatable(self):
        return self._updatable

    @property
    def sortable(self):
        return self._sortable

    @property
    def filterable(self):
        return self._filterable

    @property
    def visible(self):
        return self._visible

    @property
    def upper_case(self):
        return self._display_format == 'UpperCase'

    @property
    def date(self):
        return self._display_format == 'Date'

    @property
    def non_negative(self):
        return self._display_format == 'NonNegative'

    @property
    def value_helper(self):
        return self._value_helper

    @value_helper.setter
    def value_helper(self, value):
        # Value Help property must not be changed
        if self._value_helper is not None:
            raise RuntimeError('Cannot replace value helper {0} of {1} by {2}'
                               .format(self._value_helper, self, value))

        self._value_helper = value

    @staticmethod
    def from_etree(entity_type_property_node):
        return EntityTypeProperty(
            entity_type_property_node.get('Name'),
            entity_type_property_node.get('Type'),
            entity_type_property_node.get('Nullable'),
            entity_type_property_node.get('MaxLength'),
            entity_type_property_node.get('Precision'),
            # TODO: create a class SAP attributes
            sap_attribute_get_bool(entity_type_property_node,
                                   'unicode', True),
            sap_attribute_get_string(entity_type_property_node,
                                     'label'),
            sap_attribute_get_bool(entity_type_property_node,
                                   'creatable', True),
            sap_attribute_get_bool(entity_type_property_node,
                                   'updatable', True),
            sap_attribute_get_bool(entity_type_property_node,
                                   'sortable', True),
            sap_attribute_get_bool(entity_type_property_node,
                                   'filterable', True),
            sap_attribute_get_string(entity_type_property_node,
                                     'text'),
            sap_attribute_get_bool(entity_type_property_node,
                                   'visible', True),
            sap_attribute_get_string(entity_type_property_node,
                                     'display-format'))


class Annotation(object):

    Kinds = enum.Enum('Kinds', 'ValueHelper')

    def __init__(self, kind, target, qualifier=None):
        super(Annotation, self).__init__()

        self._kind = kind
        self._namespace, self._element = target.split('.')
        self._qualifier = qualifier

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self.target)

    @property
    def namespace(self):
        return self._namespace

    @property
    def element(self):
        return self._element

    @property
    def target(self):
        return '{0}.{1}'.format(self._namespace, self._element)

    @property
    def kind(self):
        return self._kind

    @staticmethod
    def from_etree(target, annotation_node):
        term = annotation_node.get('Term')
        if term == SAP_ANNOTATION_VALUE_LIST:
            return ValueHelper.from_etree(target, annotation_node)

        logging.warn('Unsupported Annotation({0})'.format(term))
        return None


class ExternalAnnontation(object):

    @staticmethod
    def from_etree(annotations_node):
        target = annotations_node.get('Target')
        for annotation in annotations_node.xpath('edm:Annotation',
                                                 namespaces=ANNOTATION_NAMESPACES):
            annot = Annotation.from_etree(target, annotation)
            if annot is None:
                continue
            yield annot


class ValueHelper(Annotation):

    def __init__(self, target, collection_path, label, search_supported):

        # pylint: disable=unused-argument

        super(ValueHelper, self).__init__(Annotation.Kinds.ValueHelper, target)

        self._entity_type_name, self._proprty_name = self.element.split('/')
        self._proprty = None

        self._collection_path = collection_path
        self._entity_set = None

        self._label = label
        self._parameters = list()

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self.element)

    @property
    def proprty_name(self):
        return self._proprty_name

    @property
    def proprty_entity_type_name(self):
        return self._entity_type_name

    @property
    def proprty(self):
        return self._proprty

    @proprty.setter
    def proprty(self, value):
        if self._proprty is not None:
            raise RuntimeError('Cannot replace {0} of {1} with {2}'
                               .format(self._proprty, self, value))

        if (value.entity_type.name != self.proprty_entity_type_name or
                value.name != self.proprty_name):
            raise RuntimeError('{0} cannot be an annotation of {1}'
                               .format(self, value))

        self._proprty = value

        for param in self._parameters:
            if param.local_property_name:
                etype = self._proprty.entity_type
                try:
                    param.local_property = etype.proprty(param.local_property_name)
                except KeyError:
                    raise RuntimeError('{0} of {1} points to an non existing LocalDataProperty {2} of {3}'.format(param, self, param.local_property_name, etype))

    @property
    def collection_path(self):
        return self._collection_path

    @property
    def entity_set(self):
        return self._entity_set

    @entity_set.setter
    def entity_set(self, value):
        if self._entity_set is not None:
            raise RuntimeError('Cannot replace {0} of {1} with {2}'
                               .format(self._entity_set, self, value))

        if value.name != self.collection_path:
            raise RuntimeError('{0} cannot be assigned to {1}'
                               .format(self, value))

        self._entity_set = value

        for param in self._parameters:
            if param.list_property_name:
                etype = self._entity_set.entity_type
                try:
                    param.list_property = etype.proprty(param.list_property_name)
                except KeyError:
                    raise RuntimeError('{0} of {1} points to an non existing ValueListProperty {2} of {3}'.format(param, self, param.list_property_name, etype))

    @property
    def label(self):
        return self._label

    @property
    def parameters(self):
        return self._parameters

    def local_property_param(self, name):
        for prm in self._parameters:
            if prm.local_property.name == name:
                return prm

        raise KeyError('{0} has no local property {1}'.format(self, name))

    def list_property_param(self, name):
        for prm in self._parameters:
            if prm.list_property.name == name:
                return prm

        raise KeyError('{0} has no list property {1}'.format(self, name))

    @staticmethod
    def from_etree(target, annotation_node):
        label = None
        collection_path = None
        search_supported = False
        params_node = None
        for prop_value in annotation_node.xpath('edm:Record/edm:PropertyValue',
                                                namespaces=ANNOTATION_NAMESPACES):
            rprop = prop_value.get('Property')
            if rprop == 'Label':
                label = prop_value.get('String')
            elif rprop == 'CollectionPath':
                collection_path = prop_value.get('String')
            elif rprop == 'SearchSupported':
                search_supported = prop_value.get('Bool')
            elif rprop == 'Parameters':
                params_node = prop_value

        value_helper = ValueHelper(target, collection_path, label,
                                   search_supported)

        if params_node is not None:
            for prm in params_node.xpath('edm:Collection/edm:Record',
                                         namespaces=ANNOTATION_NAMESPACES):
                param = ValueHelperParameter.from_etree(prm)
                param.value_helper = value_helper
                value_helper._parameters.append(param)

        return value_helper


class ValueHelperParameter(object):

    Direction = enum.Enum('Direction', 'In InOut Out DisplayOnly FilterOnly')

    def __init__(self, direction, local_property_name, list_property_name):
        super(ValueHelperParameter, self).__init__()

        self._direction = direction
        self._value_helper = None

        self._local_property = None
        self._local_property_name = local_property_name

        self._list_property = None
        self._list_property_name = list_property_name

    def __str__(self):
        if self._direction in [ValueHelperParameter.Direction.DisplayOnly,
                               ValueHelperParameter.Direction.FilterOnly]:
            return "{0}({1})".format(self.__class__.__name__,
                                     self._list_property_name)

        return "{0}({1}={2})".format(self.__class__.__name__,
                                     self._local_property_name,
                                     self._list_property_name)

    @property
    def value_helper(self):
        return self._value_helper

    @value_helper.setter
    def value_helper(self, value):
        if self._value_helper is not None:
            raise RuntimeError('Cannot replace {0} of {1} with {2}'
                               .format(self._value_helper, self, value))

        self._value_helper = value

    @property
    def direction(self):
        return self._direction

    @property
    def local_property_name(self):
        return self._local_property_name

    @property
    def local_property(self):
        return self._local_property

    @local_property.setter
    def local_property(self, value):
        if self._local_property is not None:
            raise RuntimeError('Cannot replace {0} of {1} with {2}'
                               .format(self._local_property, self, value))

        self._local_property = value

    @property
    def list_property_name(self):
        return self._list_property_name

    @property
    def list_property(self):
        return self._list_property

    @list_property.setter
    def list_property(self, value):
        if self._list_property is not None:
            raise RuntimeError('Cannot replace {0} of {1} with {2}'
                               .format(self._list_property, self, value))

        self._list_property = value

    @staticmethod
    def from_etree(value_help_parameter_node):
        typ = value_help_parameter_node.get('Type')
        direction = SAP_VALUE_HELPER_DIRECTIONS[typ]
        local_prop_name = None
        list_prop_name = None
        for pval in value_help_parameter_node.xpath('edm:PropertyValue',
                                                    namespaces=ANNOTATION_NAMESPACES):
            pv_name = pval.get('Property')
            if pv_name == 'LocalDataProperty':
                local_prop_name = pval.get('PropertyPath')
            elif pv_name == 'ValueListProperty':
                list_prop_name = pval.get('String')

        return ValueHelperParameter(direction, local_prop_name, list_prop_name)


class FunctionImport(Identifier):

    def __init__(self, name, return_type, entity_set, parameters, http_method='GET'):
        super(FunctionImport, self).__init__(name)

        self._entity_set_name = entity_set

        # TODO: handle Collections
        try:
            self._return_type = Typ.from_name(return_type)
        except KeyError:
            self._return_type = return_type

        self._parameters = parameters
        self._http_method = http_method

    @property
    def return_type(self):
        return self._return_type

    @property
    def entity_set_name(self):
        return self._entity_set_name

    @property
    def parameters(self):
        return self._parameters.values()

    def get_parameter(self, parameter):
        return self._parameters[parameter]

    @property
    def http_method(self):
        return self._http_method

    @staticmethod
    def from_etree(function_import_node):
        name = function_import_node.get('Name')
        entity_set = function_import_node.get('EntitySet')
        return_type = function_import_node.get('ReturnType')
        http_method = metadata_attribute_get(function_import_node, 'HttpMethod')

        parameters = dict()
        for param in function_import_node.xpath('edm:Parameter',
                                                namespaces=NAMESPACES):
            param_name = param.get('Name')
            param_type = param.get('Type')
            param_nullable = param.get('Nullable')
            param_max_length = param.get('MaxLength')
            param_precision = param.get('Precision')
            param_mode = param.get('Mode')

            parameters[param_name] = FunctionImportParameter(param_name, param_type,
                                                             param_nullable, param_max_length,
                                                             param_precision, param_mode)

        return FunctionImport(name, return_type, entity_set, parameters, http_method)


class FunctionImportParameter(VariableDeclaration):

    Modes = enum.Enum('Modes', 'In Out InOut')

    def __init__(self, name, typ, nullable, max_length, precision, mode):
        super(FunctionImportParameter,
              self).__init__(name, typ, nullable, max_length, precision)

        self._mode = mode

    @property
    def mode(self):
        return self._mode


def sap_attribute_get(node, attr):
    return node.get('{http://www.sap.com/Protocols/SAPData}%s' % (attr))


def metadata_attribute_get(node, attr):
    return node.get('{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}%s' % (attr))


def sap_attribute_get_string(node, attr):
    return sap_attribute_get(node, attr)


def sap_attribute_get_bool(node, attr, default):
    value = sap_attribute_get(node, attr)
    if value is None:
        return default

    if value == 'true':
        return True

    if value == 'false':
        return False

    raise TypeError('Not a bool attribute: {0} = {1}'.format(attr, value))


NAMESPACES = {
    'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
    'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
    'sap': 'http://www.sap.com/Protocols/SAPData',
    'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx',
    'edm': 'http://schemas.microsoft.com/ado/2008/09/edm'
}

ANNOTATION_NAMESPACES = {
    'edm': 'http://docs.oasis-open.org/odata/ns/edm'
}

SAP_VALUE_HELPER_DIRECTIONS = {
    'com.sap.vocabularies.Common.v1.ValueListParameterIn':
    ValueHelperParameter.Direction.In,
    'com.sap.vocabularies.Common.v1.ValueListParameterInOut':
    ValueHelperParameter.Direction.InOut,
    'com.sap.vocabularies.Common.v1.ValueListParameterOut':
    ValueHelperParameter.Direction.Out,
    'com.sap.vocabularies.Common.v1.ValueListParameterDisplayOnly':
    ValueHelperParameter.Direction.DisplayOnly,
    'com.sap.vocabularies.Common.v1.ValueListParameterFilterOnly':
    ValueHelperParameter.Direction.FilterOnly
}

SAP_ANNOTATION_VALUE_LIST = 'com.sap.vocabularies.Common.v1.ValueList'


class Edmx(object):

    # pylint: disable=useless-super-delegation

    def __init__(self):
        super(Edmx, self).__init__()

    @staticmethod
    def parse(metadata_xml):
        """ Build model from the XML metadata"""

        mdf = StringIO.StringIO(metadata_xml)
        # the first child element has name 'Edmx'
        edmx = etree.parse(mdf)
        edm_schemas = edmx.xpath('/edmx:Edmx/edmx:DataServices/edm:Schema',
                                 namespaces=NAMESPACES)
        schema = Schema.from_etree(edm_schemas[0])
        return schema


def schema_from_xml(metadata_xml):
    """Parses XML data and returns Schema representing OData Metadata"""

    return Edmx.parse(metadata_xml)
