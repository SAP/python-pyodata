"""
Simple stupid representation of Metadata of OData V2

Author: Jakub Filak <jakub.filak@sap.com>
Date:   2017-08-21
"""
# pylint: disable=missing-docstring,too-many-instance-attributes,too-many-arguments,protected-access,no-member,line-too-long,logging-format-interpolation,too-few-public-methods,too-many-lines

import collections
import itertools
import StringIO
import logging
import enum
import re
import datetime
from pyodata.exceptions import PyODataException, PyODataModelError
from lxml import etree

IdentifierInfo = collections.namedtuple('IdentifierInfo', 'namespace name')
TypeInfo = collections.namedtuple('TypeInfo', 'namespace name is_collection')


class Identifier(object):

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

        parts = value.split('.')

        if len(parts) == 1:
            return IdentifierInfo(None, value)

        return IdentifierInfo(parts[0], parts[1])


class Types(object):
    """Repository of all available OData types

       Since each type has instance of appropriate type, this
       repository acts as central storage for all instances. The
       rule is: don't create any type instances if not necessary,
       always reuse existing instances if possible
    """

    # dictionary of all registered types (primitive, complex and collection variants)
    Types = None

    @staticmethod
    def _build_types():
        """Create and register instances of all primitive Edm types"""

        if Types.Types is None:
            Types.Types = {}

            Types.register_type(Typ('Null', 'null'))
            Types.register_type(Typ('Edm.Binary', 'binary\'\''))
            Types.register_type(Typ('Edm.Boolean', 'false', EdmBooleanTypTraits()))
            Types.register_type(Typ('Edm.Byte', '0'))
            Types.register_type(Typ('Edm.DateTime', 'datetime\'2000-01-01T00:00\'', EdmDateTimeTypTraits()))
            Types.register_type(Typ('Edm.Decimal', '0.0M'))
            Types.register_type(Typ('Edm.Double', '0.0d'))
            Types.register_type(Typ('Edm.Single', '0.0f'))
            Types.register_type(Typ('Edm.Guid', 'guid\'00000000-0000-0000-0000-000000000000\'', EdmPrefixedTypTraits('guid')))
            Types.register_type(Typ('Edm.Int16', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.Int32', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.Int64', '0L', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.SByte', '0'))
            Types.register_type(Typ('Edm.String', '\'\'', EdmStringTypTraits()))
            Types.register_type(Typ('Edm.Time', 'time\'PT00H00M\''))
            Types.register_type(Typ('Edm.DateTimeOffset', 'datetimeoffset\'0000-00-00T00:00:00\''))

    @staticmethod
    def register_type(typ):
        """Add new  type to the type repository as well as its collection variant"""

        # build types hierarchy on first use (lazy creation)
        if Types.Types is None:
            Types._build_types()

        # register type only if it doesn't exist
        if typ.name not in Types.Types:
            Types.Types[typ.name] = typ

        # automatically create and register collection variant if not exists
        collection_name = 'Collection({})'.format(typ.name)
        if collection_name not in Types.Types:
            collection_typ = Collection(typ.name, typ)
            Types.Types[collection_name] = collection_typ

    @staticmethod
    def from_name(name):

        # build types hierarchy on first use (lazy creation)
        if Types.Types is None:
            Types._build_types()

        search_name = name

        # detect if name represents collection
        is_collection = name.lower().startswith('collection(') and name.endswith(')')
        if is_collection:
            name = name[11:-1]   # strip collection() decorator
            search_name = 'Collection({})'.format(name)

        return Types.Types[search_name]

    @staticmethod
    def parse_type_name(type_name):

        # detect if name represents collection
        is_collection = type_name.lower().startswith('collection(') and type_name.endswith(')')
        if is_collection:
            type_name = type_name[11:-1]   # strip collection() decorator

        parts = type_name.split('.')

        if len(parts) == 1:
            return TypeInfo(None, type_name, is_collection)

        if len(parts) > 1 and parts[0] == 'Edm':
            return TypeInfo(None, type_name, is_collection)

        return TypeInfo(parts[0], parts[1], is_collection)


class EdmStructTypeSerializer(object):
    """Basic implementation of (de)serialization for Edm complex types

       All properties existing in related Edm type are taken
       into account, others are ignored

       TODO: it can happen that inifinite recurision occurs for cases
       when property types are referencich each other. We need some research
       here to avoid such cases.
    """

    @staticmethod
    def to_odata(edm_type, value):

        # pylint: disable=no-self-use
        if not edm_type:
            raise PyODataException('Cannot encode value {} without complex type information'.format(value))

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.typ.traits.to_odata(value[type_prop.name])

        return result

    @staticmethod
    def from_odata(edm_type, value):

        # pylint: disable=no-self-use
        if not edm_type:
            raise PyODataException('Cannot decode value {} without complex type information'.format(value))

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.typ.traits.from_odata(value[type_prop.name])

        return result


class TypTraits(object):
    """Encapsulated differences between types"""

    def __repr__(self):
        return self.__class__.__name__

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return value

    # pylint: disable=no-self-use
    def from_odata(self, value):
        return value


class EdmPrefixedTypTraits(TypTraits):
    """Is good for all types where values have form: prefix'value'"""

    def __init__(self, prefix):
        super(EdmPrefixedTypTraits, self).__init__()
        self._prefix = prefix

    def to_odata(self, value):
        return '{}\'{}\''.format(self._prefix, value)

    def from_odata(self, value):
        matches = re.match("^{}'(.*)'$".format(self._prefix), value)
        if not matches:
            raise PyODataModelError("Malformed value {0} for primitive Edm type. Expected format is {1}'value'".format(value, self._prefix))
        return matches.group(1)


class EdmDateTimeTypTraits(EdmPrefixedTypTraits):
    """Emd.DateTime traits

       Represents date and time with values ranging from 12:00:00 midnight,
       January 1, 1753 A.D. through 11:59:59 P.M, December 9999 A.D.

       Literal form:
       datetime'yyyy-mm-ddThh:mm[:ss[.fffffff]]'
       NOTE: Spaces are not allowed between datetime and quoted portion.
       datetime is case-insensitive

       Example 1: datetime'2000-12-12T12:00'
    """

    def __init__(self):
        super(EdmDateTimeTypTraits, self).__init__('datetime')

    def to_odata(self, value):
        """Convert python datetime representation to odata format

           None: this could be done also via formatting string:
           value.strftime('%Y-%m-%dT%H:%M:%S.%f')
        """

        if not isinstance(value, datetime.datetime):
            raise PyODataModelError('Cannot convert value of type {} to odata. Datetime format is required.'.format(type(value)))

        return super(EdmDateTimeTypTraits, self).to_odata(value.isoformat())

    def from_odata(self, value):

        value = super(EdmDateTimeTypTraits, self).from_odata(value)

        try:
            value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            try:
                value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                try:
                    value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M')
                except ValueError:
                    raise PyODataModelError('Cannot decode datetime from value {}.'.format(value))

        return value


class EdmStringTypTraits(TypTraits):
    """Edm.String traits"""

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return '\'%s\'' % (value)

    # pylint: disable=no-self-use
    def from_odata(self, value):
        return value.strip('\'')


class EdmBooleanTypTraits(TypTraits):
    """Edm.Boolean traits"""

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return 'true' if value else 'false'

    # pylint: disable=no-self-use
    def from_odata(self, value):
        return value == 'true'


class EdmIntTypTraits(TypTraits):
    """All Edm Integer traits"""

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return '%d' % (value)

    # pylint: disable=no-self-use
    def from_odata(self, value):
        return int(value)


class EdmStructTypTraits(TypTraits):
    """Edm structural types (EntityType, ComplexType) traits"""

    def __init__(self, edm_type=None):
        super(EdmStructTypTraits, self).__init__()
        self._edm_type = edm_type

    # pylint: disable=no-self-use
    def to_odata(self, value):
        return EdmStructTypeSerializer.to_odata(self._edm_type, value)

    # pylint: disable=no-self-use
    def from_odata(self, value):
        return EdmStructTypeSerializer.from_odata(self._edm_type, value)


class Typ(Identifier):

    Types = None

    Kinds = enum.Enum('Kinds', 'Primitive Complex')

    def __init__(self, name, null_value, traits=TypTraits(), kind=None):
        super(Typ, self).__init__(name)

        self._null_value = null_value
        self._kind = kind if kind is not None else Typ.Kinds.Primitive  # no way how to us enum value for parameter default value
        self._traits = traits

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
    def to_odata(self, value):
        if not isinstance(value, list):
            raise PyODataException('Bad format: invalid list value {}'.format(value))

        return [self._item_type.traits.to_odata(v) for v in value]

    # pylint: disable=no-self-use
    def from_odata(self, value):
        if not isinstance(value, list):
            raise PyODataException('Bad format: invalid list value {}'.format(value))

        return [self._item_type.traits.from_odata(v) for v in value]


class VariableDeclaration(Identifier):

    MAXIMUM_LENGTH = -1

    def __init__(self, name, type_info, nullable, max_length, precision):
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

        self._precision = precision

    @property
    def type_info(self):
        return self._type_info

    @property
    def typ(self):
        return self._typ

    @typ.setter
    def typ(self, value):
        if self._typ is not None:
            raise RuntimeError('Cannot replace {0} of {1} by {2}'
                               .format(self._typ, self, value))

        if value.name != self._type_info[1]:
            raise RuntimeError('{0} cannot be the type of {1}'
                               .format(value, self))

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


class Schema(object):

    class Declaration(object):

        def __init__(self, namespace):
            super(Schema.Declaration, self).__init__()

            self.namespace = namespace

            self.entity_types = dict()
            self.complex_types = dict()
            self.entity_sets = dict()
            self.function_imports = dict()
            self.associations = dict()
            self.association_sets = dict()

        def list_entity_types(self):
            return self.entity_types.values()

        def list_complex_types(self):
            return self.complex_types.values()

        def list_entity_sets(self):
            return self.entity_sets.values()

        def list_function_imports(self):
            return self.function_imports.values()

        def list_associations(self):
            return self.associations.values()

        def list_association_sets(self):
            return self.association_sets.values()

        def add_entity_type(self, etype):
            """Add new  type to the type repository as well as its collection variant"""

            self.entity_types[etype.name] = etype

            # automatically create and register collection variant if not exists
            collection_type_name = 'Collection({})'.format(etype.name)
            self.entity_types[collection_type_name] = Collection(etype.name, etype)

        def add_complex_type(self, ctype):
            """Add new complex type to the type repository as well as its collection variant"""

            self.complex_types[ctype.name] = ctype

            # automatically create and register collection variant if not exists
            collection_type_name = 'Collection({})'.format(ctype.name)
            self.complex_types[collection_type_name] = Collection(ctype.name, ctype)

    def __init__(self):
        super(Schema, self).__init__()

        self._decls = dict()

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, ','.join(self.namespaces))

    @property
    def namespaces(self):
        return self._decls.keys()

    def typ(self, type_name, namespace=None):
        """Returns either EntityType or ComplexType that matches the name.
        """

        for type_space in (self.entity_type, self.complex_type):
            try:
                return type_space(type_name, namespace=namespace)
            except KeyError:
                pass

        raise KeyError('Type {} does not exist in Schema{}'
                       .format(type_name, ' Namespace ' + namespace if namespace else ''))

    def entity_type(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].entity_types[type_name]
            except KeyError:
                raise KeyError('EntityType {} does not exist in Schema Namespace {}'
                               .format(type_name, namespace))

        for decl in self._decls.values():
            try:
                return decl.entity_types[type_name]
            except KeyError:
                pass

        raise KeyError('EntityType {} does not exist in any Schema Namespace'.format(type_name))

    def complex_type(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].complex_types[type_name]
            except KeyError:
                raise KeyError('ComplexType {} does not exist in Schema Namespace {}'
                               .format(type_name, namespace))

        for decl in self._decls.values():
            try:
                return decl.complex_types[type_name]
            except KeyError:
                pass

        raise KeyError('ComplexType {} does not exist in any Schema Namespace'.format(type_name))

    def get_type(self, type_info):

        # construct search name based on collection information
        search_name = type_info[1] if not type_info[2] else 'Collection({})'.format(type_info[1])

        # first look for type in primitive types
        try:
            return Types.from_name(search_name)
        except KeyError:
            pass

        # then look for type in entity types
        try:
            return self.entity_type(search_name, type_info[0])
        except KeyError:
            pass

        # then look for type in complex types
        try:
            return self.complex_type(search_name, type_info[0])
        except KeyError:
            pass

        raise PyODataModelError('Neither primitive types nor types parsed from service metadata contain requested type {}'.format(type_info[1]))

    @property
    def entity_types(self):
        return [entity_type for entity_type in itertools.chain(*(decl.list_entity_types() for decl in self._decls.values()))]

    @property
    def complex_types(self):
        return [complex_type for complex_type in itertools.chain(*(decl.list_complex_types() for decl in self._decls.values()))]

    def entity_set(self, set_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].entity_sets[set_name]
            except KeyError:
                raise KeyError('EntitySet {} does not exist in Schema Namespace {}'
                               .format(set_name, namespace))

        for decl in self._decls.values():
            try:
                return decl.entity_set[set_name]
            except KeyError:
                pass

        raise KeyError('EntitySet {} does not exist in any Schema Namespace'.format(set_name))

    @property
    def entity_sets(self):
        return [entity_set for entity_set in itertools.chain(*(decl.list_entity_sets() for decl in self._decls.values()))]

    def function_import(self, function_import, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].function_imports[function_import]
            except KeyError:
                raise KeyError('FunctionImport {} does not exist in Schema Namespace {}'
                               .format(function_import, namespace))

        for decl in self._decls.values():
            try:
                return decl.function_imports[function_import]
            except KeyError:
                pass

        raise KeyError('FunctionImport {} does not exist in any Schema Namespace'.format(function_import))

    @property
    def function_imports(self):
        return [func_import for func_import in itertools.chain(*(decl.list_function_imports() for decl in self._decls.values()))]

    def association(self, association_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].associations[association_name]
            except KeyError:
                raise KeyError('Association {} does not exist in namespace {}'.format(association_name,
                                                                                      namespace))
        for decl in self._decls.values():
            try:
                return decl.associations[association_name]
            except KeyError:
                pass

    @property
    def associations(self):
        return [association for association in itertools.chain(*(decl.list_associations()
                                                                 for decl in self._decls.values()))]

    def association_set_by_association(self, association, namespace=None):
        if namespace is not None:
            for association_set in self._decls[namespace].association_sets.values():
                if association_set.association_type == association:
                    return association_set
            raise KeyError('Association set with association type {} does not exist in namespace {}'.format(association,
                                                                                                            namespace))
        for decl in self._decls.values():
            for association_set in decl.association_sets.values():
                if association_set.association_type == association:
                    return association_set
        raise KeyError('Association set with association type {} does not exist'.format(association))


    def association_set(self, set_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].association_sets[set_name]
            except KeyError:
                raise KeyError('Association set {} does not exist in namespace {}'.format(set_name,
                                                                                          namespace))
        for decl in self._decls.values():
            try:
                return decl.association_sets[set_name]
            except KeyError:
                pass

    @property
    def association_sets(self):
        return [association_set for association_set in itertools.chain(*(decl.list_association_sets()
                                                                         for decl in self._decls.values()))]

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    @staticmethod
    def from_etree(schema_nodes):
        schema = Schema()

        # Parse Schema nodes by parts to get over the problem of not-yet known
        # entity types referenced by entity sets, function imports and
        # annotations.

        # First, process EntityType and ComplexType nodes. They have almost no dependencies on other elements.
        for schema_node in schema_nodes:
            namespace = schema_node.get('Namespace')
            decl = Schema.Declaration(namespace)
            schema._decls[namespace] = decl

            for complex_type in schema_node.xpath('edm:ComplexType',
                                                  namespaces=NAMESPACES):
                ctype = ComplexType.from_etree(complex_type)
                decl.add_complex_type(ctype)

            for entity_type in schema_node.xpath('edm:EntityType',
                                                 namespaces=NAMESPACES):
                etype = EntityType.from_etree(entity_type)
                decl.add_entity_type(etype)

        # resolve types of properties
        for stype in itertools.chain(schema.entity_types, schema.complex_types):
            if stype.kind == Typ.Kinds.Complex:
                # skip collections (no need to assign any types since type of collection
                # items is resolved separately
                if stype.is_collection:
                    continue

                for prop in stype.proprties():
                    prop.typ = schema.get_type(prop.type_info)

        # Then, process Associations nodes because they refer EntityTypes and
        # they are referenced by AssociationSets.
        for schema_node in schema_nodes:
            namespace = schema_node.get('Namespace')
            decl = schema._decls[namespace]

            for association in schema_node.xpath('edm:Association',
                                                 namespaces=NAMESPACES):
                assoc = Association.from_etree(association)
                for end_role in assoc.end_roles.values():
                    try:
                        # search and assign entity type (it must exist)
                        if end_role.entity_type_info.namespace is None:
                            end_role.entity_type_info.namespace = namespace

                        etype = schema.entity_type(
                            end_role.entity_type_info.name,
                            end_role.entity_type_info.namespace)

                        end_role.entity_type = etype
                    except KeyError:
                        raise PyODataModelError('Entity type {} does not exist in scheme {}'
                                                .format(end_role.entity_type_name, decl.namespace))

                if assoc.referential_constraint is not None:
                    role_names = [end_role.role for end_role in assoc.end_roles.values()]
                    principal_role = assoc.referential_constraint.principal

                    # Check if the role was defined in the current association
                    if principal_role.name not in role_names:
                        raise RuntimeError('Role {} was not defined in association {}'.format(principal_role.name,
                                                                                              assoc.name))

                    # Check if principal role properties exist
                    for proprty in principal_role.property_names:
                        role_name = principal_role.name
                        entity_type = schema.entity_type(assoc.end_role(role_name).entity_type_name)
                        try:
                            entity_type.proprty(proprty)
                        except KeyError:
                            raise RuntimeError('Property {} does not exist in {}'
                                               .format(proprty, entity_type.name))

                    dependent_role = assoc.referential_constraint.dependent

                    # Check if the role was defined in the current association
                    if dependent_role.name not in role_names:
                        raise RuntimeError('Role {} was not defined in association {}'.format(dependent_role.name,
                                                                                              assoc.name))

                    # Check if dependent role properties exist
                    for proprty in dependent_role.property_names:
                        role_name = dependent_role.name
                        entity_type = schema.entity_type(assoc.end_role(role_name).entity_type_name)
                        try:
                            entity_type.proprty(proprty)
                        except KeyError:
                            raise RuntimeError('Property {} does not exist in {}'
                                               .format(proprty, entity_type.name))

                decl.associations[assoc.name] = assoc

        # resolve navigation properties
        for stype in schema.entity_types:
            # skip collections
            if stype.is_collection:
                continue

            for nav_prop in stype.nav_proprties:
                assoc = schema.association(nav_prop.association_info.name, nav_prop.association_info.namespace)
                nav_prop.association = assoc

        # Then, process EntitySet, FunctionImport and AssociationSet nodes.
        for schema_node in schema_nodes:
            namespace = schema_node.get('Namespace')
            decl = schema._decls[namespace]

            for entity_set in schema_node.xpath('edm:EntityContainer/edm:EntitySet',
                                                namespaces=NAMESPACES):
                eset = EntitySet.from_etree(entity_set)
                eset.entity_type = schema.entity_type(eset.entity_type_info[1],
                                                      namespace=eset.entity_type_info[0])
                decl.entity_sets[eset.name] = eset

            for function_import in schema_node.xpath('edm:EntityContainer/edm:FunctionImport',
                                                     namespaces=NAMESPACES):
                efn = FunctionImport.from_etree(function_import)

                # complete type information for return type and parameters
                efn.return_type = schema.get_type(efn.return_type_info)
                for param in efn.parameters:
                    param.typ = schema.get_type(param.type_info)
                decl.function_imports[efn.name] = efn

            for association_set in schema_node.xpath('edm:AssociationSet',
                                                     namespaces=NAMESPACES):
                assoc_set = AssociationSet.from_etree(association_set)
                scheme_namespace, association_name = assoc_set.association_type_name.split('.', 1)

                try:
                    assoc_set.association_type = schema.association(association_name)
                except KeyError:
                    raise RuntimeError('Association {} does not exist in scheme {}'.format(association_name,
                                                                                           decl.namespace))

                for key, value in assoc_set.end_roles.items():
                    # Check if entity set exists in current scheme
                    try:
                        schema.entity_set(key, decl.namespace)
                    except KeyError:
                        raise RuntimeError('Entity {} does not exist in scheme {}'.format(key,
                                                                                          decl.namespace))
                    # Check if role is defined in Association
                    try:
                        assoc_set.association_type.end_role(value)
                    except KeyError:
                        raise RuntimeError('Role {} is not defined in association {}'.format(value,
                                                                                             assoc_set.association_type_name))

                decl.association_sets[assoc_set.name] = assoc_set

        # Finally, process Annotation nodes when all Scheme nodes are completely processed.
        for schema_node in schema_nodes:
            for annotation_group in schema_node.xpath('edm:Annotations',
                                                      namespaces=ANNOTATION_NAMESPACES):
                for annotation in ExternalAnnontation.from_etree(annotation_group):
                    if not annotation.element_namespace != schema.namespaces:
                        logging.warn('{0} not in the namespaces {1}'
                                     .format(annotation, ','.join(schema.namespaces)))
                        continue

                    if annotation.kind == Annotation.Kinds.ValueHelper:

                        try:
                            annotation.entity_set = schema.entity_set(
                                annotation.collection_path, namespace=annotation.element_namespace)
                        except KeyError:
                            raise RuntimeError('Entity Set {0} for {1} does not exist'
                                               .format(annotation.collection_path, annotation))

                        try:
                            vh_type = schema.typ(
                                annotation.proprty_entity_type_name, namespace=annotation.element_namespace)
                        except KeyError:
                            raise RuntimeError('Target Type {0} of {1} does not exist'.format(annotation.proprty_entity_type_name, annotation))

                        try:
                            target_proprty = vh_type.proprty(annotation.proprty_name)
                        except KeyError:
                            raise RuntimeError('Target Property {0} of {1} as defined in {2} does not exist'.format(annotation.proprty_name, vh_type, annotation))

                        annotation.proprty = target_proprty
                        target_proprty.value_helper = annotation

        return schema


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
        return self._properties[property_name]

    def proprties(self):
        return self._properties.values()

    @classmethod
    def from_etree(cls, type_node):
        name = type_node.get('Name')
        label = sap_attribute_get_string(type_node, 'label')
        is_value_list = sap_attribute_get_bool(type_node,
                                               'value-list', False)

        stype = cls(name, label, is_value_list)

        for proprty in type_node.xpath('edm:Property',
                                       namespaces=NAMESPACES):
            stp = StructTypeProperty.from_etree(proprty)

            if stp.name in stype._properties:
                raise KeyError('{0} already has property {1}'
                               .format(stype, stp.name))

            stype._properties[stp.name] = stp

        # We have to update the property when
        # all properites are loaded because
        # there might be links between them.
        for ctp in stype._properties.values():
            ctp.struct_type = stype

        return stype

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
        return self._nav_properties.values()

    def nav_proprty(self, property_name):
        return self._nav_properties[property_name]

    @classmethod
    def from_etree(cls, type_node):

        etype = super(EntityType, cls).from_etree(type_node)

        for proprty in type_node.xpath('edm:Key/edm:PropertyRef',
                                       namespaces=NAMESPACES):
            etype._key.append(etype.proprty(proprty.get('Name')))

        for proprty in type_node.xpath('edm:NavigationProperty',
                                       namespaces=NAMESPACES):
            navp = NavigationTypeProperty.from_etree(proprty)

            if navp.name in etype._nav_properties:
                raise KeyError('{0} already has navigation property {1}'
                               .format(etype, navp.name))

            etype._nav_properties[navp.name] = navp

        return etype


class EntitySet(Identifier):

    def __init__(self, name, entity_type_info, creatable, updatable,
                 deletable, searchable):
        super(EntitySet, self).__init__(name)

        self._entity_type_info = entity_type_info
        self._entity_type = None
        self._creatable = creatable
        self._updatable = updatable
        self._deletable = deletable
        self._searchable = searchable

    @property
    def entity_type_info(self):
        return self._entity_type_info

    @property
    def entity_type(self):
        return self._entity_type

    @entity_type.setter
    def entity_type(self, value):
        if self._entity_type is not None:
            raise RuntimeError('Cannot replace {0} of {1} to {2}'
                               .format(self._entity_type, self, value))

        if value.name != self.entity_type_info[1]:
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
        et_info = Types.parse_type_name(entity_set_node.get('EntityType'))

        # TODO: create a class SAP attributes
        creatable = sap_attribute_get_bool(entity_set_node,
                                           'creatable', True)
        updatable = sap_attribute_get_bool(entity_set_node,
                                           'updatable', True)
        deletable = sap_attribute_get_bool(entity_set_node,
                                           'deletable', True)
        searchable = sap_attribute_get_bool(entity_set_node,
                                            'searchable', True)

        return EntitySet(name, et_info, creatable,
                         updatable, deletable, searchable)


class StructTypeProperty(VariableDeclaration):
    """Property of structure types (Entity/Complex type)

       Type of the property can be:
        * primitive type
        * complex type
        * enumeration type (in version 4)
        * collection of one of previous
    """
    # pylint: disable=too-many-locals
    def __init__(self, name, type_info, nullable, max_length, precision, uncode,
                 label, creatable, updatable, sortable, filterable, text,
                 visible, display_format, value_list):
        super(StructTypeProperty, self).__init__(name, type_info, nullable,
                                                 max_length, precision)

        self._value_helper = None
        self._struct_type = None
        self._uncode = uncode
        self._label = label
        self._creatable = creatable
        self._updatable = updatable
        self._sortable = sortable
        self._filterable = filterable
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
            raise RuntimeError('Cannot replace {0} of {1} to {2}'
                               .format(self._struct_type, self, value))

        self._struct_type = value

        if self._text_proprty_name is not None:
            try:
                self._text_proprty = self._struct_type.proprty(self._text_proprty_name)
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

    @property
    def value_list(self):
        return self._value_list

    @value_helper.setter
    def value_helper(self, value):
        # Value Help property must not be changed
        if self._value_helper is not None:
            raise RuntimeError('Cannot replace value helper {0} of {1} by {2}'
                               .format(self._value_helper, self, value))

        self._value_helper = value

    @staticmethod
    def from_etree(entity_type_property_node):

        return StructTypeProperty(
            entity_type_property_node.get('Name'),
            Types.parse_type_name(entity_type_property_node.get('Type')),
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
                                     'display-format'),
            sap_attribute_get_string(entity_type_property_node,
                                     'value-list'),)


class NavigationTypeProperty(VariableDeclaration):
    """Defines a navigation property, which provides a reference to the other end of an association

       Unlike properties defined with the Property element, navigation properties do not define the
       shape and characteristics of data. They provide a way to navigate an association between two
       entity types.

       Note that navigation properties are optional on both entity types at the ends of an association.
       If you define a navigation property on one entity type at the end of an association, you do not
       have to define a navigation property on the entity type at the other end of the association.

       The data type returned by a navigation property is determined by the multiplicity of its remote
       association end. For example, suppose a navigation property, OrdersNavProp, exists on a Customer
       entity type and navigates a one-to-many association between Customer and Order. Because the
       remote association end for the navigation property has multiplicity many (*), its data type is
       a collection (of Order). Similarly, if a navigation property, CustomerNavProp, exists on the Order
       entity type, its data type would be Customer since the multiplicity of the remote end is one (1).
    """
    def __init__(self, name, from_role_name, to_role_name, association_info):
        super(NavigationTypeProperty, self).__init__(name, None, False, None, None)

        self.from_role_name = from_role_name
        self.to_role_name = to_role_name

        self._association_info = association_info
        self._association = None

    @property
    def association_info(self):
        return self._association_info

    @property
    def association(self):
        return self._association

    @association.setter
    def association(self, value):

        if self._association is not None:
            raise PyODataModelError('Cannot replace {0} of {1} to {2}'
                                    .format(self._association, self, value))

        if value.name != self._association_info.name:
            raise PyODataModelError('{0} cannot be the type of {1}'
                                    .format(value, self))

        self._association = value

    @property
    def to_role(self):
        return self._association.end_role(self.to_role_name)

    @property
    def typ(self):
        return self.to_role.entity_type

    @staticmethod
    def from_etree(node):

        return NavigationTypeProperty(
            node.get('Name'),
            node.get('FromRole'),
            node.get('ToRole'),
            Identifier.parse(node.get('Relationship')))


class EndRole(object):

    MULTIPLICITY_ONE = '1'
    MULTIPLICITY_ZERO_OR_ONE = '0..1'
    MULTIPLICITY_ZERO_OR_MORE = '*'

    def __init__(self, entity_type_info, multiplicity, role):
        self._entity_type_info = entity_type_info
        self._entity_type = None
        self._multiplicity = multiplicity
        self._role = role

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, self.role)

    @property
    def entity_type_info(self):
        return self._entity_type_info

    @property
    def entity_type_name(self):
        return self._entity_type_info.name

    @property
    def entity_type(self):
        return self._entity_type

    @entity_type.setter
    def entity_type(self, value):

        if self._entity_type is not None:
            raise PyODataModelError('Cannot replace {0} of {1} to {2}'
                                    .format(self._entity_type, self, value))

        if value.name != self._entity_type_info.name:
            raise PyODataModelError('{0} cannot be the type of {1}'
                                    .format(value, self))

        self._entity_type = value

    @property
    def multiplicity(self):
        return self._multiplicity

    @property
    def role(self):
        return self._role

    @staticmethod
    def from_etree(end_role_node):
        entity_type_info = Types.parse_type_name(end_role_node.get('Type'))
        multiplicity = end_role_node.get('Multiplicity')
        role = end_role_node.get('Role')

        return EndRole(entity_type_info, multiplicity, role)


class ReferentialConstraintRole(object):

    def __init__(self, name, property_names):
        self._name = name
        self._property_names = property_names

    @property
    def name(self):
        return self._name

    @property
    def property_names(self):
        return self._property_names


class PrincipalRole(ReferentialConstraintRole):
    pass


class DependentRole(ReferentialConstraintRole):
    pass


class ReferentialConstraint(object):

    def __init__(self, principal, dependent):
        self._principal = principal
        self._dependent = dependent

    @property
    def principal(self):
        return self._principal

    @property
    def dependent(self):
        return self._dependent

    @staticmethod
    def from_etree(referential_constraint_node):
        principal = referential_constraint_node.xpath('edm:Principal', namespaces=NAMESPACES)
        if len(principal) != 1:
            raise RuntimeError('Referential constraint must contain exactly one principal element')

        principal_name = principal[0].get('Role')
        if principal_name is None:
            raise RuntimeError('Principal role name was not specified')

        principal_refs = []
        for property_ref in principal[0].xpath('edm:PropertyRef', namespaces=NAMESPACES):
            principal_refs.append(property_ref.get('Name'))
        if not principal_refs:
            raise RuntimeError('In role {} should be at least one principal property defined'
                               .format(principal_name))

        dependent = referential_constraint_node.xpath('edm:Dependent', namespaces=NAMESPACES)
        if len(dependent) != 1:
            raise RuntimeError('Referential constraint must contain exactly one dependent element')

        dependent_name = dependent[0].get('Role')
        if dependent_name is None:
            raise RuntimeError('Dependent role name was not specified')

        dependent_refs = []
        for property_ref in dependent[0].xpath('edm:PropertyRef', namespaces=NAMESPACES):
            dependent_refs.append(property_ref.get('Name'))
        if len(principal_refs) != len(dependent_refs):
            raise RuntimeError('Number of properties should be equal for the principal {} and the dependent {}'
                               .format(principal_name, dependent_name))

        return ReferentialConstraint(PrincipalRole(principal_name, principal_refs),
                                     DependentRole(dependent_name, dependent_refs))


class Association(object):
    """Defines a relationship between two entity types.

       An association must specify the entity types that are involved in
       the relationship and the possible number of entity types at each
       end of the relationship, which is known as the multiplicity.
       The multiplicity of an association end can have a value of one (1),
       zero or one (0..1), or many (*). This information is specified in
       two child End elements.
    """

    def __init__(self, name):
        self._name = name
        self._referential_constraint = None
        self._end_roles = dict()

    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name

    @property
    def end_roles(self):
        return self._end_roles

    def end_role(self, end_role):
        return self._end_roles[end_role]

    @property
    def referential_constraint(self):
        return self._referential_constraint

    @staticmethod
    def from_etree(association_node):
        name = association_node.get('Name')
        association = Association(name)

        for end in association_node.xpath('edm:End', namespaces=NAMESPACES):
            end_role = EndRole.from_etree(end)
            if end_role.role is None:
                raise RuntimeError('Role is not specified in the association {}'.format(name))
            association._end_roles[end_role.role] = end_role

        if len(association._end_roles) != 2:
            raise RuntimeError('Association {} does not have two end roles'.format(name))

        refer = association_node.xpath('edm:ReferentialConstraint', namespaces=NAMESPACES)
        if len(refer) > 1:
            raise RuntimeError('In association {} is defined more than one referential constraint'.format(name))

        if not refer:
            referential_constraint = None
        else:
            referential_constraint = ReferentialConstraint.from_etree(refer[0])

        association._referential_constraint = referential_constraint

        return association


class AssociationSet(object):

    def __init__(self, name, association_type_name, end_roles):
        self._name = name
        self._association_type_name = association_type_name
        self._association_type = None
        self._end_roles = end_roles

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name

    @property
    def association_type(self):
        return self._association_type

    @property
    def association_type_name(self):
        return self._association_type_name

    @property
    def end_roles(self):
        return self._end_roles

    @association_type.setter
    def association_type(self, value):
        if self._association_type is not None:
            raise RuntimeError('Cannot replace {} of {} with {}'
                               .format(self._association_type, self, value))
        self._association_type = value

    @staticmethod
    def from_etree(association_set_node):
        name = association_set_node.get('Name')
        association_type = association_set_node.get('Association')
        end_roles = {}

        for end_role in association_set_node.xpath('edm:End', namespaces=NAMESPACES):
            entity_set = end_role.get('EntitySet')
            role = end_role.get('Role')
            end_roles[entity_set] = role

        return AssociationSet(name, association_type, end_roles)


class Annotation(object):

    Kinds = enum.Enum('Kinds', 'ValueHelper')

    def __init__(self, kind, target, qualifier=None):
        super(Annotation, self).__init__()

        self._kind = kind
        self._element_namespace, self._element = target.split('.')
        self._qualifier = qualifier

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self.target)

    @property
    def element_namespace(self):
        return self._element_namespace

    @property
    def element(self):
        return self._element

    @property
    def target(self):
        return '{0}.{1}'.format(self._element_namespace, self._element)

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

        if (value.struct_type.name != self.proprty_entity_type_name or
                value.name != self.proprty_name):
            raise RuntimeError('{0} cannot be an annotation of {1}'
                               .format(self, value))

        self._proprty = value

        for param in self._parameters:
            if param.local_property_name:
                etype = self._proprty.struct_type
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
            raise RuntimeError('Cannot replace {0} of {1} by {2}'
                               .format(self._return_type, self, value))

        if value.name != self.return_type_info[1]:
            raise RuntimeError('{0} cannot be the type of {1}'
                               .format(value, self))

        self._return_type = value

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
        http_method = metadata_attribute_get(function_import_node, 'HttpMethod')
        rt_info = Types.parse_type_name(function_import_node.get('ReturnType'))

        parameters = dict()
        for param in function_import_node.xpath('edm:Parameter',
                                                namespaces=NAMESPACES):
            param_name = param.get('Name')
            param_type_info = Types.parse_type_name(param.get('Type'))
            param_nullable = param.get('Nullable')
            param_max_length = param.get('MaxLength')
            param_precision = param.get('Precision')
            param_mode = param.get('Mode')

            parameters[param_name] = FunctionImportParameter(param_name, param_type_info,
                                                             param_nullable, param_max_length,
                                                             param_precision, param_mode)

        return FunctionImport(name, rt_info, entity_set, parameters, http_method)


class FunctionImportParameter(VariableDeclaration):

    Modes = enum.Enum('Modes', 'In Out InOut')

    def __init__(self, name, type_info, nullable, max_length, precision, mode):
        super(FunctionImportParameter,
              self).__init__(name, type_info, nullable, max_length, precision)

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
        schema = Schema.from_etree(edm_schemas)
        return schema


def schema_from_xml(metadata_xml):
    """Parses XML data and returns Schema representing OData Metadata"""

    return Edmx.parse(metadata_xml)
