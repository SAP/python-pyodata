# pylint: disable=too-many-lines, missing-docstring, too-many-arguments, too-many-instance-attributes

import collections
import itertools
import logging
from abc import abstractmethod
from enum import Enum
from typing import Union

from pyodata.policies import ParserError
from pyodata.config import Config
from pyodata.exceptions import PyODataModelError, PyODataException, PyODataParserError

from pyodata.model.type_traits import TypTraits, EdmStructTypTraits


IdentifierInfo = collections.namedtuple('IdentifierInfo', 'namespace name')
TypeInfo = collections.namedtuple('TypeInfo', 'namespace name is_collection')


def modlog():
    return logging.getLogger("Elements")


def build_element(element_name: Union[str, type], config: Config, **kwargs):
    """
    This function is responsible for resolving which implementation is to be called for parsing EDM element. It's a
    primitive implementation of dynamic dispatch, thus there exist table where all supported elements are assigned
    parsing function. When elements class or element name is passed we search this table. If key exists we call the
    corresponding function with kwargs arguments, otherwise we raise an exception.

    Important to note is that although elements among version, can have the same name their properties can differ
    significantly thus class representing ElementX in V2 is not necessarily equal to ElementX in V4.

    :param element_name: Passing class is preferred as it does not add 'magic' strings to our code but if you
                         can't import the class of the element pass the class name instead.
    :param config: Config
    :param kwargs: Any arguments that are to be passed to the build function e. g. etree, schema...

    :return: Object
    """

    if not isinstance(element_name, str):
        element_name = element_name.__name__

    callbacks = config.odata_version.build_functions()
    for clb in callbacks:
        if element_name == clb.__name__:
            return callbacks[clb](config, **kwargs)

    raise PyODataParserError(f'{element_name} is unsupported in {config.odata_version.__name__}')


def build_annotation(term: str, config: Config, **kwargs):
    """
    Similarly to build_element this function purpoas is to resolve build function for annotations. There are two
    main differences:
        1) This method accepts child of Annotation. Every child has to implement static method term() -> str

        2) Annotation has to have specified target. This target is reference to type, property and so on, because of
        that there is no repository of annotations in schema. Thus this method does return void, but it might have
        side effect.
    # http://docs.oasis-open.org/odata/odata/v4.0/errata03/os/complete/part3-csdl/odata-v4.0-errata03-os-part3-csdl-complete.html#_Toc453752619

    :param term: Term defines what does the annotation do. Specification advise clients to ignore unknown terms
                 by default.
    :param config: Config
    :param kwargs: Any arguments that are to be passed to the build function e. g. etree, schema...

    :return: void
    """

    annotations = config.odata_version.annotations()
    try:
        for annotation in annotations:
            alias, element = term.rsplit('.', 1)
            namespace = config.aliases.get(alias, '')

            if term == annotation.term() or f'{namespace}.{element}' == annotation.term():
                annotations[annotation](config, **kwargs)
                return

        raise PyODataParserError(f'Annotation with term {term} is unsupported in {config.odata_version.__name__}')
    except PyODataException as ex:
        config.err_policy(ParserError.ANNOTATION).resolve(ex)


class NullType:
    def __init__(self, name):
        self.name = name

    def __getattr__(self, item):
        raise PyODataModelError(f'Cannot access this type. An error occurred during parsing type stated in '
                                f'xml({self.name}) was not found, therefore it has been replaced with NullType.')


class NullAnnotation:
    def __init__(self, term):
        self.term = term

    def __getattr__(self, item):
        raise PyODataModelError(f'Cannot access this annotation. An error occurred during parsing '
                                f'annotation(term = {self.term}), therefore it has been replaced with NullAnnotation.')


class Identifier:
    def __init__(self, name):
        super(Identifier, self).__init__()

        self._name = name

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, self._name)

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name

    @staticmethod
    def parse(value):
        segments = value.split('/')
        path = []
        for segment in segments:
            parts = segment.split('.')

            if len(parts) == 1:
                path.append(IdentifierInfo(None, parts[-1]))
            else:
                path.append(IdentifierInfo('.'.join(parts[:-1]), parts[-1]))

        if len(path) == 1:
            return path[0]
        return path


class Types:
    """ Repository of all available OData types in given version

       Since each type has instance of appropriate type, this
       repository acts as central storage for all instances. The
       rule is: don't create any type instances if not necessary,
       always reuse existing instances if possible
    """

    @staticmethod
    def register_type(typ: 'Typ', config: Config):
        """Add new type to the ODATA version type repository as well as its collection variant"""

        o_version = config.odata_version

        # register type only if it doesn't exist
        if typ.name not in o_version.Types:
            o_version.Types[typ.name] = typ

        # automatically create and register collection variant if not exists
        collection_name = 'Collection({})'.format(typ.name)
        if collection_name not in o_version.Types:
            collection_typ = Collection(typ.name, typ)
            o_version.Types[collection_name] = collection_typ

    @staticmethod
    def from_name(name, config: Config) -> 'Typ':
        o_version = config.odata_version

        # build types hierarchy on first use (lazy creation)
        if not o_version.Types:
            o_version.Types = dict()
            for typ in o_version.primitive_types():
                Types.register_type(typ, config)

        search_name = name

        # detect if name represents collection
        is_collection = name.lower().startswith('collection(') and name.endswith(')')
        if is_collection:
            name = name[11:-1]  # strip collection() decorator
            search_name = 'Collection({})'.format(name)

        try:
            return o_version.Types[search_name]
        except KeyError:
            raise PyODataModelError(f'Requested primitive type {search_name} is not supported in this version of ODATA')

    @staticmethod
    def parse_type_name(type_name):

        # detect if name represents collection
        is_collection = type_name.lower().startswith('collection(') and type_name.endswith(')')
        if is_collection:
            type_name = type_name[11:-1]  # strip collection() decorator

        identifier = Identifier.parse(type_name)

        if identifier.namespace == 'Edm':
            return TypeInfo(None, type_name, is_collection)

        return TypeInfo(identifier.namespace, identifier.name, is_collection)


class Typ(Identifier):
    Types = None

    Kinds = Enum('Kinds', 'Primitive Complex')

    # pylint: disable=line-too-long
    def __init__(self, name, null_value, traits=TypTraits(), kind=None):
        super(Typ, self).__init__(name)

        self._null_value = null_value
        self._kind = kind if kind is not None else Typ.Kinds.Primitive  # no way how to us enum value for parameter default value
        self._traits = traits
        self._annotation = None

    @property
    def null_value(self):
        return self._null_value

    @property
    def traits(self):
        return self._traits

    @property
    def is_collection(self):
        return False

    @property
    def kind(self):
        return self._kind

    @property
    def annotation(self) -> 'Annotation':
        return self._annotation

    @annotation.setter
    def annotation(self, value: 'Annotation'):
        self._annotation = value

    # pylint: disable=no-member
    @Identifier.name.setter
    def name(self, value: str):
        self._name = value


class Collection(Typ):
    """Represents collection items"""

    def __init__(self, name, item_type):
        super(Collection, self).__init__(name, [], kind=item_type.kind)
        self._item_type = item_type

    def __repr__(self):
        return 'Collection({})'.format(repr(self._item_type))

    @property
    def is_collection(self):
        return True

    @property
    def item_type(self):
        return self._item_type

    @property
    def traits(self):
        return self

    # pylint: disable=no-self-use
    def to_literal(self, value):
        if not isinstance(value, list):
            raise PyODataException('Bad format: invalid list value {}'.format(value))

        return [self._item_type.traits.to_literal(v) for v in value]

    # pylint: disable=no-self-use
    def from_json(self, value):
        if not isinstance(value, list):
            raise PyODataException('Bad format: invalid list value {}'.format(value))

        return [self._item_type.traits.from_json(v) for v in value]


class VariableDeclaration(Identifier):
    MAXIMUM_LENGTH = -1

    def __init__(self, name, type_info, nullable, max_length, precision, scale):
        super(VariableDeclaration, self).__init__(name)

        self._type_info = type_info
        self._typ = None

        self._nullable = bool(nullable)

        if not max_length:
            self._max_length = None
        elif max_length.upper() == 'MAX':
            self._max_length = VariableDeclaration.MAXIMUM_LENGTH
        else:
            self._max_length = int(max_length)

        if not precision:
            self._precision = None
        else:
            self._precision = int(precision)
        if not scale:
            self._scale = 0
        else:
            self._scale = int(scale)
        self._check_scale_value()

    @property
    def type_info(self):
        return self._type_info

    @property
    def typ(self):
        return self._typ

    @typ.setter
    def typ(self, value):
        if self._typ is not None:
            raise PyODataModelError('Cannot replace {0} of {1} by {2}'.format(self._typ, self, value))

        if value.name != self._type_info[1]:
            raise PyODataModelError('{0} cannot be the type of {1}'.format(value, self))

        self._typ = value

    @property
    def nullable(self):
        return self._nullable

    @property
    def max_length(self):
        return self._max_length

    @property
    def precision(self):
        return self._precision

    @property
    def scale(self):
        return self._scale

    def _check_scale_value(self):
        if self._precision and self._scale > self._precision:
            raise PyODataModelError('Scale value ({}) must be less than or equal to precision value ({})'
                                    .format(self._scale, self._precision))


class Schema:
    class Declaration:
        def __init__(self, namespace):
            super(Schema.Declaration, self).__init__()

            self.namespace = namespace

            self.entity_types = dict()
            self.complex_types = dict()
            self.enum_types = dict()
            self.entity_sets = dict()
            self.function_imports = dict()
            self.associations = dict()
            self.association_sets = dict()
            self.type_definitions: [str, Typ] = dict()

        def list_entity_types(self):
            return list(self.entity_types.values())

        def list_complex_types(self):
            return list(self.complex_types.values())

        def list_enum_types(self):
            return list(self.enum_types.values())

        def list_entity_sets(self):
            return list(self.entity_sets.values())

        def list_function_imports(self):
            return list(self.function_imports.values())

        def list_associations(self):
            return list(self.associations.values())

        def list_association_sets(self):
            return list(self.association_sets.values())

        def list_type_definitions(self):
            return list(self.type_definitions.values())

        def add_entity_type(self, etype):
            """Add new  type to the type repository as well as its collection variant"""

            self.entity_types[etype.name] = etype

            # automatically create and register collection variant if not exists
            if isinstance(etype, NullType):
                return

            collection_type_name = 'Collection({})'.format(etype.name)
            self.entity_types[collection_type_name] = Collection(etype.name, etype)

        def add_complex_type(self, ctype):
            """Add new complex type to the type repository as well as its collection variant"""

            self.complex_types[ctype.name] = ctype

            # automatically create and register collection variant if not exists
            if isinstance(ctype, NullType):
                return

            collection_type_name = 'Collection({})'.format(ctype.name)
            self.complex_types[collection_type_name] = Collection(ctype.name, ctype)

        def add_enum_type(self, etype):
            """Add new enum type to the type repository"""
            self.enum_types[etype.name] = etype

        def add_type_definition(self, tdefinition: Typ):
            """Add new type definition to the type repository"""
            self.type_definitions[tdefinition.name] = tdefinition

    class Declarations(dict):

        def __getitem__(self, key):
            try:
                return super(Schema.Declarations, self).__getitem__(key)
            except KeyError:
                raise PyODataModelError('There is no Schema Namespace {}'.format(key))

    def __init__(self, config: Config):
        super(Schema, self).__init__()

        self._decls = Schema.Declarations()
        self._config = config

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, ','.join(self.namespaces))

    @property
    def namespaces(self):
        return list(self._decls.keys())

    @property
    def config(self):
        return self._config

    def typ(self, type_name, namespace=None):
        """Returns either EntityType, ComplexType or EnumType that matches the name.
        """

        for type_space in (self.entity_type, self.complex_type, self.enum_type):
            try:
                return type_space(type_name, namespace=namespace)
            except PyODataModelError:
                pass

        raise PyODataModelError('Type {} does not exist in Schema{}'
                                .format(type_name, ' Namespace ' + namespace if namespace else ''))

    def entity_type(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].entity_types[type_name]
            except KeyError:
                raise PyODataModelError('EntityType {} does not exist in Schema Namespace {}'
                                        .format(type_name, namespace))

        for decl in list(self._decls.values()):
            try:
                return decl.entity_types[type_name]
            except KeyError:
                pass

        raise PyODataModelError('EntityType {} does not exist in any Schema Namespace'.format(type_name))

    def complex_type(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].complex_types[type_name]
            except KeyError:
                raise PyODataModelError('ComplexType {} does not exist in Schema Namespace {}'
                                        .format(type_name, namespace))

        for decl in list(self._decls.values()):
            try:
                return decl.complex_types[type_name]
            except KeyError:
                pass

        raise PyODataModelError('ComplexType {} does not exist in any Schema Namespace'.format(type_name))

    def enum_type(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].enum_types[type_name]
            except KeyError:
                raise PyODataModelError(f'EnumType {type_name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.enum_types[type_name]
            except KeyError:
                pass

        raise PyODataModelError(f'EnumType {type_name} does not exist in any Schema Namespace')

    def type_definition(self, name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].type_definitions[name]
            except KeyError:
                raise PyODataModelError(f'EnumType {name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.type_definitions[name]
            except KeyError:
                pass

        raise PyODataModelError(f'EnumType {name} does not exist in any Schema Namespace')

    def get_type(self, type_info):

        # construct search name based on collection information
        search_name = type_info.name if not type_info.is_collection else 'Collection({})'.format(type_info.name)

        # first look for type in primitive types
        try:
            return Types.from_name(search_name, self.config)
        except PyODataModelError:
            pass

        # then look for type in type definitions
        try:
            return self.type_definition(search_name, type_info.namespace)
        except PyODataModelError:
            pass

        # then look for type in entity types
        try:
            return self.entity_type(search_name, type_info.namespace)
        except PyODataModelError:
            pass

        # then look for type in complex types
        try:
            return self.complex_type(search_name, type_info.namespace)
        except PyODataModelError:
            pass

        # then look for type in enum types
        try:
            return self.enum_type(search_name, type_info.namespace)
        except PyODataModelError:
            pass

        raise PyODataModelError(
            'Neither primitive types nor types parsed from service metadata contain requested type {}'
            .format(type_info.name))

    @property
    def entity_types(self):
        return list(itertools.chain(*(decl.list_entity_types() for decl in list(self._decls.values()))))

    @property
    def complex_types(self):
        return list(itertools.chain(*(decl.list_complex_types() for decl in list(self._decls.values()))))

    @property
    def enum_types(self):
        return list(itertools.chain(*(decl.list_enum_types() for decl in list(self._decls.values()))))

    def entity_set(self, set_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].entity_sets[set_name]
            except KeyError:
                raise PyODataModelError('EntitySet {} does not exist in Schema Namespace {}'
                                        .format(set_name, namespace))

        for decl in list(self._decls.values()):
            try:
                return decl.entity_sets[set_name]
            except KeyError:
                pass

        raise PyODataModelError('EntitySet {} does not exist in any Schema Namespace'.format(set_name))

    @property
    def entity_sets(self):
        return list(itertools.chain(*(decl.list_entity_sets() for decl in list(self._decls.values()))))

    def function_import(self, function_import, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].function_imports[function_import]
            except KeyError:
                raise PyODataModelError('FunctionImport {} does not exist in Schema Namespace {}'
                                        .format(function_import, namespace))

        for decl in list(self._decls.values()):
            try:
                return decl.function_imports[function_import]
            except KeyError:
                pass

        raise PyODataModelError('FunctionImport {} does not exist in any Schema Namespace'.format(function_import))

    @property
    def function_imports(self):
        return list(itertools.chain(*(decl.list_function_imports() for decl in list(self._decls.values()))))

    def check_role_property_names(self, role, entity_type_name, namespace):
        for proprty in role.property_names:
            try:
                entity_type = self.entity_type(entity_type_name, namespace)
            except KeyError:
                raise PyODataModelError('EntityType {} does not exist in Schema Namespace {}'
                                        .format(entity_type_name, namespace))
            try:
                entity_type.proprty(proprty)
            except KeyError:
                raise PyODataModelError('Property {} does not exist in {}'.format(proprty, entity_type.name))


class StructType(Typ):
    def __init__(self, name, label, is_value_list):
        super(StructType, self).__init__(name, None, EdmStructTypTraits(self), Typ.Kinds.Complex)

        self._label = label
        self._is_value_list = is_value_list
        self._key = list()
        self._properties = dict()

    @property
    def label(self):
        return self._label

    @property
    def is_value_list(self):
        return self._is_value_list

    def proprty(self, property_name):
        try:
            return self._properties[property_name]
        except KeyError:
            raise PyODataModelError(f'Property {property_name} not found on {self}')

    def proprties(self):
        return list(self._properties.values())

    # implementation of Typ interface
    @property
    def is_collection(self):
        return False

    @property
    def kind(self):
        return Typ.Kinds.Complex

    @property
    def null_value(self):
        return None

    @property
    def traits(self):
        # return self._traits
        return EdmStructTypTraits(self)


class ComplexType(StructType):
    """Representation of Edm.ComplexType"""


class EntityType(StructType):
    def __init__(self, name, label, is_value_list):
        super(EntityType, self).__init__(name, label, is_value_list)

        self._key = list()
        self._nav_properties = dict()

    @property
    def key_proprties(self):
        return list(self._key)

    @property
    def nav_proprties(self):
        """Gets the navigation properties defined for this entity type"""
        return list(self._nav_properties.values())

    def nav_proprty(self, property_name):
        try:
            return self._nav_properties[property_name]
        except KeyError as ex:
            raise PyODataModelError(f'{self} does not contain navigation property {property_name}') from ex


class EntitySet(Identifier):
    def __init__(self, name, entity_type_info, addressable, creatable, updatable, deletable, searchable, countable,
                 pageable, topable, req_filter, label):
        super(EntitySet, self).__init__(name)

        self._entity_type_info = entity_type_info
        self._entity_type = None
        self._addressable = addressable
        self._creatable = creatable
        self._updatable = updatable
        self._deletable = deletable
        self._searchable = searchable
        self._countable = countable
        self._pageable = pageable
        self._topable = topable
        self._req_filter = req_filter
        self._label = label

    @property
    def entity_type_info(self):
        return self._entity_type_info

    @property
    def entity_type(self):
        return self._entity_type

    @entity_type.setter
    def entity_type(self, value):
        if self._entity_type is not None:
            raise PyODataModelError('Cannot replace {0} of {1} to {2}'.format(self._entity_type, self, value))

        if value.name != self.entity_type_info[1]:
            raise PyODataModelError('{0} cannot be the type of {1}'.format(value, self))

        self._entity_type = value

    @property
    def addressable(self):
        return self._addressable

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

    @property
    def countable(self):
        return self._countable

    @property
    def pageable(self):
        return self._pageable

    @property
    def topable(self):
        return self._topable

    @property
    def requires_filter(self):
        return self._req_filter

    @property
    def label(self):
        return self._label


class StructTypeProperty(VariableDeclaration):
    """Property of structure types (Entity/Complex type)

       Type of the property can be:
        * primitive type
        * complex type
        * enumeration type (in version 4)
        * collection of one of previous
    """

    # pylint: disable=too-many-locals
    def __init__(self, name, type_info, nullable, max_length, precision, scale, uncode, label, creatable, updatable,
                 sortable, filterable, filter_restr, req_in_filter, text, visible, display_format, value_list):
        super(StructTypeProperty, self).__init__(name, type_info, nullable, max_length, precision, scale)

        self._value_helper = None
        self._struct_type = None
        self._uncode = uncode
        self._label = label
        self._creatable = creatable
        self._updatable = updatable
        self._sortable = sortable
        self._filterable = filterable
        self._filter_restr = filter_restr
        self._req_in_filter = req_in_filter
        self._text_proprty_name = text
        self._visible = visible
        self._display_format = display_format
        self._value_list = value_list

        # Lazy loading
        self._text_proprty = None

    @property
    def struct_type(self):
        return self._struct_type

    @struct_type.setter
    def struct_type(self, value):

        if self._struct_type is not None:
            raise PyODataModelError('Cannot replace {0} of {1} to {2}'.format(self._struct_type, self, value))

        self._struct_type = value

        if self._text_proprty_name is not None:
            try:
                self._text_proprty = self._struct_type.proprty(self._text_proprty_name)
            except KeyError:
                # TODO: resolve EntityType of text property
                if '/' not in self._text_proprty_name:
                    raise PyODataModelError('The attribute sap:text of {1} is set to non existing Property \'{0}\''
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
    def filter_restriction(self):
        return self._filter_restr

    @property
    def required_in_filter(self):
        return self._req_in_filter

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

    @property
    def value_list(self):
        return self._value_list

    @value_helper.setter
    def value_helper(self, value):
        # Value Help property must not be changed
        if self._value_helper is not None:
            raise PyODataModelError('Cannot replace value helper {0} of {1} by {2}'
                                    .format(self._value_helper, self, value))

        self._value_helper = value


class Annotation:

    def __init__(self, target, qualifier=None):
        super(Annotation, self).__init__()

        self._element_namespace, self._element = target.split('.')
        self._qualifier = qualifier

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self.target)

    @staticmethod
    @abstractmethod
    def term() -> str:
        pass

    @property
    def element_namespace(self):
        return self._element_namespace

    @property
    def element(self):
        return self._element

    @property
    def target(self):
        return '{0}.{1}'.format(self._element_namespace, self._element)


class ValueHelper(Annotation):
    def __init__(self, target, collection_path, label, search_supported):

        # pylint: disable=unused-argument

        super(ValueHelper, self).__init__(target)

        self._entity_type_name, self._proprty_name = self.element.split('/')
        self._proprty = None

        self._collection_path = collection_path
        self._entity_set = None

        self._label = label
        self._parameters = list()

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self.element)

    @staticmethod
    def term() -> str:
        return 'com.sap.vocabularies.Common.v1.ValueList'

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
            raise PyODataModelError('Cannot replace {0} of {1} with {2}'.format(self._proprty, self, value))

        if value.struct_type.name != self.proprty_entity_type_name or value.name != self.proprty_name:
            raise PyODataModelError('{0} cannot be an annotation of {1}'.format(self, value))

        self._proprty = value

        for param in self._parameters:
            if param.local_property_name:
                etype = self._proprty.struct_type
                try:
                    param.local_property = etype.proprty(param.local_property_name)
                except PyODataModelError:
                    raise PyODataModelError('{0} of {1} points to an non existing LocalDataProperty {2} of {3}'.format(
                        param, self, param.local_property_name, etype))

    @property
    def collection_path(self):
        return self._collection_path

    @property
    def entity_set(self):
        return self._entity_set

    @entity_set.setter
    def entity_set(self, value):
        if self._entity_set is not None:
            raise PyODataModelError('Cannot replace {0} of {1} with {2}'.format(self._entity_set, self, value))

        if value.name != self.collection_path:
            raise PyODataModelError('{0} cannot be assigned to {1}'.format(self, value))

        self._entity_set = value

        for param in self._parameters:
            if param.list_property_name:
                etype = self._entity_set.entity_type
                try:
                    param.list_property = etype.proprty(param.list_property_name)
                except PyODataModelError:
                    raise PyODataModelError('{0} of {1} points to an non existing ValueListProperty {2} of {3}'.format(
                        param, self, param.list_property_name, etype))

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

        raise PyODataModelError('{0} has no local property {1}'.format(self, name))

    def list_property_param(self, name):
        for prm in self._parameters:
            if prm.list_property.name == name:
                return prm

        raise PyODataModelError('{0} has no list property {1}'.format(self, name))


class ValueHelperParameter():
    Direction = Enum('Direction', 'In InOut Out DisplayOnly FilterOnly')

    def __init__(self, direction, local_property_name, list_property_name):
        super(ValueHelperParameter, self).__init__()

        self._direction = direction
        self._value_helper = None

        self._local_property = None
        self._local_property_name = local_property_name

        self._list_property = None
        self._list_property_name = list_property_name

    def __str__(self):
        if self._direction in [ValueHelperParameter.Direction.DisplayOnly, ValueHelperParameter.Direction.FilterOnly]:
            return "{0}({1})".format(self.__class__.__name__, self._list_property_name)

        return "{0}({1}={2})".format(self.__class__.__name__, self._local_property_name, self._list_property_name)

    @property
    def value_helper(self):
        return self._value_helper

    @value_helper.setter
    def value_helper(self, value):
        if self._value_helper is not None:
            raise PyODataModelError('Cannot replace {0} of {1} with {2}'.format(self._value_helper, self, value))

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
            raise PyODataModelError('Cannot replace {0} of {1} with {2}'.format(self._local_property, self, value))

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
            raise PyODataModelError('Cannot replace {0} of {1} with {2}'.format(self._list_property, self, value))

        self._list_property = value


class FunctionImport(Identifier):
    def __init__(self, name, return_type_info, entity_set, parameters, http_method='GET'):
        super(FunctionImport, self).__init__(name)

        self._entity_set_name = entity_set
        self._return_type_info = return_type_info
        self._return_type = None
        self._parameters = parameters
        self._http_method = http_method

    @property
    def return_type_info(self):
        return self._return_type_info

    @property
    def return_type(self):
        return self._return_type

    @return_type.setter
    def return_type(self, value):
        if self._return_type is not None:
            raise PyODataModelError('Cannot replace {0} of {1} by {2}'.format(self._return_type, self, value))

        if value.name != self.return_type_info[1]:
            raise PyODataModelError('{0} cannot be the type of {1}'.format(value, self))

        self._return_type = value

    @property
    def entity_set_name(self):
        return self._entity_set_name

    @property
    def parameters(self):
        return list(self._parameters.values())

    def get_parameter(self, parameter):
        return self._parameters[parameter]

    @property
    def http_method(self):
        return self._http_method


class FunctionImportParameter(VariableDeclaration):
    Modes = Enum('Modes', 'In Out InOut')

    def __init__(self, name, type_info, nullable, max_length, precision, scale, mode):
        super(FunctionImportParameter, self).__init__(name, type_info, nullable, max_length, precision, scale)

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
