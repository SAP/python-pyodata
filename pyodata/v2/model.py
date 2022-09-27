"""
Simple representation of Metadata of OData V2

Author: Jakub Filak <jakub.filak@sap.com>
Date:   2017-08-21
"""
# pylint: disable=missing-docstring,too-many-instance-attributes,too-many-arguments,protected-access,no-member,line-too-long,logging-format-interpolation,too-few-public-methods,too-many-lines, too-many-public-methods

import base64
import collections
import datetime
from enum import Enum, auto
import io
import itertools
import logging
import re
import warnings
from abc import ABC, abstractmethod

from lxml import etree

from pyodata.exceptions import PyODataException, PyODataModelError, PyODataParserError

LOGGER_NAME = 'pyodata.model'
FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE = False
FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE = False

IdentifierInfo = collections.namedtuple('IdentifierInfo', 'namespace name')
TypeInfo = collections.namedtuple('TypeInfo', 'namespace name is_collection')


def modlog():
    return logging.getLogger(LOGGER_NAME)


class NullAssociation:
    def __init__(self, name):
        self.name = name

    def __getattr__(self, item):
        raise PyODataModelError('Cannot access this association. An error occurred during parsing '
                                'association metadata due to that annotation has been omitted.')


class NullType:
    def __init__(self, name):
        self.name = name

    def __getattr__(self, item):
        raise PyODataModelError(f'Cannot access this type. An error occurred during parsing '
                                f'type stated in xml({self.name}) was not found, therefore it has been replaced with NullType.')


class ErrorPolicy(ABC):
    @abstractmethod
    def resolve(self, ekseption):
        pass


class PolicyFatal(ErrorPolicy):
    def resolve(self, ekseption):
        raise ekseption


class PolicyWarning(ErrorPolicy):
    def __init__(self):
        logging.basicConfig(format='%(levelname)s: %(message)s')
        self._logger = logging.getLogger()

    def resolve(self, ekseption):
        self._logger.warning('[%s] %s', ekseption.__class__.__name__, str(ekseption))


class PolicyIgnore(ErrorPolicy):
    def resolve(self, ekseption):
        pass


class ParserError(Enum):
    PROPERTY = auto()
    ANNOTATION = auto()
    ASSOCIATION = auto()

    ENUM_TYPE = auto()
    ENTITY_TYPE = auto()
    COMPLEX_TYPE = auto()


class Config:

    def __init__(self,
                 custom_error_policies=None,
                 default_error_policy=None,
                 xml_namespaces=None,
                 retain_null=False):

        """
        :param custom_error_policies: {ParserError: ErrorPolicy} (default None)
                                      Used to specified individual policies for XML tags. See documentation for more
                                      details.

        :param default_error_policy: ErrorPolicy (default PolicyFatal)
                                     If custom policy is not specified for the tag, the default policy will be used.

        :param xml_namespaces: {str: str} (default None)

        :param retain_null: bool (default False)
                            If true, do not substitute missing (and null-able) values with default value.
        """

        self._custom_error_policy = custom_error_policies

        if default_error_policy is None:
            default_error_policy = PolicyFatal()

        self._default_error_policy = default_error_policy

        if xml_namespaces is None:
            xml_namespaces = {}

        self._namespaces = xml_namespaces

        self._retain_null = retain_null

    def err_policy(self, error: ParserError):
        if self._custom_error_policy is None:
            return self._default_error_policy

        return self._custom_error_policy.get(error, self._default_error_policy)

    def set_default_error_policy(self, policy: ErrorPolicy):
        self._custom_error_policy = None
        self._default_error_policy = policy

    def set_custom_error_policy(self, policies: dict):
        self._custom_error_policy = policies

    @property
    def namespaces(self):
        return self._namespaces

    @namespaces.setter
    def namespaces(self, value: dict):
        self._namespaces = value

    @property
    def retain_null(self):
        return self._retain_null


class Identifier:
    def __init__(self, name):
        super(Identifier, self).__init__()

        self._name = name

    def __repr__(self):
        return f"{self.__class__.__name__}({self._name})"

    def __str__(self):
        return f"{self.__class__.__name__}({self._name})"

    @property
    def name(self):
        return self._name

    @staticmethod
    def parse(value):
        parts = value.split('.')

        if len(parts) == 1:
            return IdentifierInfo(None, value)

        return IdentifierInfo('.'.join(parts[:-1]), parts[-1])


class Types:
    """Repository of all available OData V2 primitive types + their Collection variants

       Since each type has instance of appropriate type, this
       repository acts as central storage for all instances. The
       rule is: don't create any type instances if not necessary,
       always reuse existing instances if possible
    """

    Types = None

    @staticmethod
    def _build_types():
        """Create and register instances of all primitive Edm types"""

        if Types.Types is None:
            Types.Types = {}

            Types.register_type(Typ('Null', 'null'))
            Types.register_type(Typ('Edm.Binary', 'binary\'\'', EdmBinaryTypTraits('(?:binary|X)')))
            Types.register_type(Typ('Edm.Boolean', 'false', EdmBooleanTypTraits()))
            Types.register_type(Typ('Edm.Byte', '0'))
            Types.register_type(Typ('Edm.DateTime', 'datetime\'1753-01-01T00:00\'', EdmDateTimeTypTraits()))
            Types.register_type(Typ('Edm.Decimal', '0.0M'))
            Types.register_type(Typ('Edm.Double', '0.0d', EdmFPNumTypTraits.edm_double()))
            Types.register_type(Typ('Edm.Single', '0.0f', EdmFPNumTypTraits.edm_single()))
            Types.register_type(Typ('Edm.Float', '0.0d', EdmFPNumTypTraits.edm_float()))
            Types.register_type(
                Typ('Edm.Guid', 'guid\'00000000-0000-0000-0000-000000000000\'', EdmPrefixedTypTraits('guid')))
            Types.register_type(Typ('Edm.Int16', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.Int32', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.Int64', '0L', EdmLongIntTypTraits()))
            Types.register_type(Typ('Edm.SByte', '0'))
            Types.register_type(Typ('Edm.String', '\'\'', EdmStringTypTraits()))
            Types.register_type(Typ('Edm.Time', 'time\'PT00H00M\''))
            Types.register_type(
                Typ('Edm.DateTimeOffset', 'datetimeoffset\'1753-01-01T00:00:00Z\'', EdmDateTimeOffsetTypTraits()))

    @staticmethod
    def register_type(typ):
        """Add new  type to the type repository as well as its collection variant"""

        # build types hierarchy on first use (lazy creation)
        if Types.Types is None:
            Types._build_types()

        # register type only if it doesn't exist
        # pylint: disable=unsupported-membership-test
        if typ.name not in Types.Types:
            # pylint: disable=unsupported-assignment-operation
            Types.Types[typ.name] = typ

        # automatically create and register collection variant if not exists
        collection_name = f'Collection({typ.name})'
        # pylint: disable=unsupported-membership-test
        if collection_name not in Types.Types:
            collection_typ = Collection(typ.name, typ)
            # pylint: disable=unsupported-assignment-operation
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
            name = name[11:-1]  # strip collection() decorator
            search_name = f'Collection({name})'

        # pylint: disable=unsubscriptable-object
        return Types.Types[search_name]

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


class EdmStructTypeSerializer:
    """Basic implementation of (de)serialization for Edm complex types

       All properties existing in related Edm type are taken
       into account, others are ignored

       TODO: it can happen that inifinite recurision occurs for cases
       when property types are referencich each other. We need some research
       here to avoid such cases.
    """

    @staticmethod
    def to_literal(edm_type, value):

        # pylint: disable=no-self-use
        if not edm_type:
            raise PyODataException(f'Cannot encode value {value} without complex type information')

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.to_literal(value[type_prop.name])

        return result

    @staticmethod
    def from_json(edm_type, value):

        # pylint: disable=no-self-use
        if not edm_type:
            raise PyODataException(f'Cannot decode value {value} without complex type information')

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.from_json(value[type_prop.name])

        return result

    @staticmethod
    def from_literal(edm_type, value):

        # pylint: disable=no-self-use
        if not edm_type:
            raise PyODataException(f'Cannot decode value {value} without complex type information')

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.from_literal(value[type_prop.name])

        return result


class TypTraits:
    """Encapsulated differences between types"""

    def __repr__(self):
        return self.__class__.__name__

    # pylint: disable=no-self-use
    def to_literal(self, value):
        return value

    # pylint: disable=no-self-use
    def from_json(self, value):
        return value

    def to_json(self, value):
        return value

    def from_literal(self, value):
        return value


class EdmPrefixedTypTraits(TypTraits):
    """Is good for all types where values have form: prefix'value'"""

    def __init__(self, prefix):
        super(EdmPrefixedTypTraits, self).__init__()
        self._prefix = prefix

    def to_literal(self, value):
        return '{}\'{}\''.format(self._prefix, value)

    def from_literal(self, value):
        matches = re.match(f"^{self._prefix}'(.*)'$", value)
        if not matches:
            raise PyODataModelError(
                f"Malformed value {value} for primitive Edm type. Expected format is {self._prefix}'value'")
        return matches.group(1)


class EdmBinaryTypTraits(EdmPrefixedTypTraits):
    """Edm.Binary traits"""

    def to_literal(self, value):
        binary = base64.b64decode(value, validate=True)
        return f"binary'{base64.b16encode(binary).decode()}'"

    def from_literal(self, value):
        binary = base64.b16decode(super().from_literal(value), casefold=True)
        return base64.b64encode(binary).decode()


def ms_since_epoch_to_datetime(value, tzinfo):
    """Convert milliseconds since midnight 1.1.1970 to datetime"""
    try:
        # https://stackoverflow.com/questions/36179914/timestamp-out-of-range-for-platform-localtime-gmtime-function
        return datetime.datetime(1970, 1, 1, tzinfo=tzinfo) + datetime.timedelta(milliseconds=int(value))
    except (ValueError, OverflowError):
        min_ticks = -62135596800000
        max_ticks = 253402300799999
        if FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE and int(value) < min_ticks:
            # Some service providers return false minimal date values.
            # -62135596800000 is the lowest value PyOData could read.
            # This workaround fixes this issue and returns 0001-01-01 00:00:00+00:00 in such a case.
            return datetime.datetime(year=1, day=1, month=1, tzinfo=tzinfo)
        if FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE and int(value) > max_ticks:
            return datetime.datetime(year=9999, day=31, month=12, tzinfo=tzinfo)
        raise PyODataModelError(f'Cannot decode datetime from value {value}. '
                                f'Possible value range: {min_ticks} to {max_ticks}. '
                                f'You may fix this by setting `FIX_SCREWED_UP_MINIMAL_DATETIME_VALUE` '
                                f' or `FIX_SCREWED_UP_MAXIMUM_DATETIME_VALUE` as a workaround.')


def parse_datetime_literal(value):
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        try:
            return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M')
            except ValueError:
                raise PyODataModelError(f'Cannot decode datetime from value {value}.')


class EdmDateTimeTypTraits(EdmPrefixedTypTraits):
    """Edm.DateTime traits

       Represents date and time with values ranging from 12:00:00 midnight,
       January 1, 1753 A.D. through 11:59:59 P.M, December 9999 A.D.

       Literal form:
       datetime'yyyy-mm-ddThh:mm[:ss[.fffffff]]'
       NOTE: Spaces are not allowed between datetime and quoted portion.
       datetime is case-insensitive

       Example 1: datetime'2000-12-12T12:00'
       JSON has following format: /Date(1516614510000)/
       https://blogs.sap.com/2017/01/05/date-and-time-in-sap-gateway-foundation/
    """

    def __init__(self):
        super(EdmDateTimeTypTraits, self).__init__('datetime')

    def to_literal(self, value):
        """Convert python datetime representation to literal format

           None: this could be done also via formatting string:
           value.strftime('%Y-%m-%dT%H:%M:%S.%f')
        """

        if not isinstance(value, datetime.datetime):
            raise PyODataModelError(
                f'Cannot convert value of type {type(value)} to literal. Datetime format is required.')

        if value.tzinfo != datetime.timezone.utc:
            raise PyODataModelError('Edm.DateTime accepts only UTC')

        # Sets timezone to none to avoid including timezone information in the literal form.
        return super(EdmDateTimeTypTraits, self).to_literal(value.replace(tzinfo=None).isoformat())

    def to_json(self, value):
        if isinstance(value, str):
            return value

        if value.tzinfo != datetime.timezone.utc:
            raise PyODataModelError('Edm.DateTime accepts only UTC')

        # Converts datetime into timestamp in milliseconds in UTC timezone as defined in ODATA specification
        # https://www.odata.org/documentation/odata-version-2-0/json-format/
        # See also: https://docs.python.org/3/library/datetime.html#datetime.datetime.timestamp
        ticks = (value - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)) / datetime.timedelta(milliseconds=1)
        return f'/Date({int(ticks)})/'

    def from_json(self, value):

        if value is None:
            return None

        matches = re.match(r"^/Date\((?P<milliseconds_since_epoch>-?\d+)(?P<offset_in_minutes>[+-]\d+)?\)/$", value)
        try:
            milliseconds_since_epoch = matches.group('milliseconds_since_epoch')
        except AttributeError:
            raise PyODataModelError(
                f"Malformed value {value} for primitive Edm.DateTime type."
                " Expected format is /Date(<ticks>[±<offset>])/")
        try:
            offset_in_minutes = int(matches.group('offset_in_minutes') or 0)
            timedelta = datetime.timedelta(minutes=offset_in_minutes)
        except ValueError:
            raise PyODataModelError(
                f"Malformed value {value} for primitive Edm.DateTime type."
                " Expected format is /Date(<ticks>[±<offset>])/")
        except AttributeError:
            timedelta = datetime.timedelta()  # Missing offset is interpreted as UTC
        # Might raise a PyODataModelError exception
        return ms_since_epoch_to_datetime(milliseconds_since_epoch, datetime.timezone.utc) + timedelta

    def from_literal(self, value):

        if value is None:
            return None

        value = super(EdmDateTimeTypTraits, self).from_literal(value)

        # Note: parse_datetime_literal raises a PyODataModelError exception on invalid formats
        return parse_datetime_literal(value).replace(tzinfo=datetime.timezone.utc)


class EdmDateTimeOffsetTypTraits(EdmPrefixedTypTraits):
    """Edm.DateTimeOffset traits

       Represents date and time, plus an offset in minutes from UTC, with values ranging from 12:00:00 midnight,
       January 1, 1753 A.D. through 11:59:59 P.M, December 9999 A.D

       Literal forms:
       datetimeoffset'yyyy-mm-ddThh:mm[:ss]±ii:nn' (works for all time zones)
       datetimeoffset'yyyy-mm-ddThh:mm[:ss]Z' (works only for UTC)
       NOTE: Spaces are not allowed between datetimeoffset and quoted portion.
       The datetime part is case-insensitive, the offset one is not.

       Example 1: datetimeoffset'1970-01-01T00:00:01+00:30'
        - /Date(1000+0030)/ (As DateTime, but with a 30 minutes timezone offset)
       Example 1: datetimeoffset'1970-01-01T00:00:01-00:60'
        - /Date(1000-0030)/ (As DateTime, but with a negative 60 minutes timezone offset)
       https://blogs.sap.com/2017/01/05/date-and-time-in-sap-gateway-foundation/
    """

    def __init__(self):
        super(EdmDateTimeOffsetTypTraits, self).__init__('datetimeoffset')

    def to_literal(self, value):
        """Convert python datetime representation to literal format"""

        if not isinstance(value, datetime.datetime) or value.utcoffset() is None:
            raise PyODataModelError(
                f'Cannot convert value of type {type(value)} to literal. Datetime format including offset is required.')

        return super(EdmDateTimeOffsetTypTraits, self).to_literal(value.isoformat())

    def to_json(self, value):
        # datetime.timestamp() does not work due to its limited precision
        offset_in_minutes = int(value.utcoffset() / datetime.timedelta(minutes=1))
        ticks = int((value - datetime.datetime(1970, 1, 1, tzinfo=value.tzinfo)) / datetime.timedelta(milliseconds=1))
        return f'/Date({ticks}{offset_in_minutes:+05})/'

    def from_json(self, value):
        # special edge case:
        # datetimeoffset'yyyy-mm-ddThh:mm[:ss]' = defaults to UTC, when offset value is not provided in response
        #   by service, but the metadata is EdmDateTimeOffset
        # intentionally just for from_json, generation of to_json should always provide timezone info
        matches = re.match(r"^/Date\((?P<milliseconds_since_epoch>-?\d+)(?P<offset_in_minutes>[+-]\d+)?\)/$", value)
        try:
            milliseconds_since_epoch = matches.group('milliseconds_since_epoch')
            if matches.group('offset_in_minutes') is not None:
                offset_in_minutes = int(matches.group('offset_in_minutes'))
            else:
                offset_in_minutes = 0
        except (ValueError, AttributeError):
            raise PyODataModelError(
                f"Malformed value {value} for primitive Edm.DateTimeOffset type."
                " Expected format is /Date(<ticks>±<offset>)/")

        tzinfo = datetime.timezone(datetime.timedelta(minutes=offset_in_minutes))
        # Might raise a PyODataModelError exception
        return ms_since_epoch_to_datetime(milliseconds_since_epoch, tzinfo)

    def from_literal(self, value):

        if value is None:
            return None

        value = super(EdmDateTimeOffsetTypTraits, self).from_literal(value)

        try:
            # Note: parse_datetime_literal raises a PyODataModelError exception on invalid formats
            if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value, flags=re.ASCII | re.IGNORECASE):
                datetime_part = value[:-1]
                tz_info = datetime.timezone.utc
            else:
                match = re.match(r'(?P<datetime>.+)(?P<sign>[\\+-])(?P<hours>\d{2}):(?P<minutes>\d{2})',
                                 value,
                                 flags=re.ASCII)
                datetime_part = match.group('datetime')
                tz_offset = datetime.timedelta(hours=int(match.group('hours')),
                                               minutes=int(match.group('minutes')))
                tz_sign = -1 if match.group('sign') == '-' else 1
                tz_info = datetime.timezone(tz_sign * tz_offset)
            return parse_datetime_literal(datetime_part).replace(tzinfo=tz_info)
        except (ValueError, AttributeError):
            raise PyODataModelError(f'Cannot decode datetimeoffset from value {value}.')


class EdmStringTypTraits(TypTraits):
    """Edm.String traits"""

    # pylint: disable=no-self-use
    def to_literal(self, value):
        return '\'%s\'' % (value)

    # pylint: disable=no-self-use
    def from_json(self, value):
        return value.strip('\'')

    def from_literal(self, value):
        return value.strip('\'')


class EdmBooleanTypTraits(TypTraits):
    """Edm.Boolean traits"""

    # pylint: disable=no-self-use
    def to_literal(self, value):
        return 'true' if value else 'false'

    # pylint: disable=no-self-use
    def from_json(self, value):
        return value

    def from_literal(self, value):
        return value == 'true'


class EdmIntTypTraits(TypTraits):
    """All Edm Integer traits"""

    # pylint: disable=no-self-use
    def to_literal(self, value):
        return '%d' % (value)

    # pylint: disable=no-self-use
    def from_json(self, value):
        return int(value)

    def from_literal(self, value):
        return int(value)


class EdmLongIntTypTraits(TypTraits):
    """All Edm Integer for big numbers traits"""

    # pylint: disable=no-self-use
    def to_literal(self, value):
        return '%dL' % (value)

    # pylint: disable=no-self-use
    def from_json(self, value):
        if value[-1] == 'L':
            return int(value[:-1])

        return int(value)

    def from_literal(self, value):
        return self.from_json(value)


class EdmFPNumTypTraits(TypTraits):
    """Edm Floating Point Number traits"""

    def __init__(self, precision, suffix, conversion):
        self.precision = precision
        self.suffix = suffix
        self.conversion = conversion

    def __repr__(self):
        parent = super(EdmFPNumTypTraits, self).__repr__()

        return f'{parent}({self.precision},{self.suffix})'

    @staticmethod
    def edm_float():
        return EdmFPNumTypTraits(7, 'd', '{:E}')

    @staticmethod
    def edm_double():
        return EdmFPNumTypTraits(15, 'd', '{:E}')

    @staticmethod
    def edm_single():
        return EdmFPNumTypTraits(7, 'f', '{:f}')

    # pylint: disable=no-self-use
    def to_literal(self, value):
        return self.conversion.format(value)

    def to_json(self, value):
        return self.to_literal(value)

    # pylint: disable=no-self-use
    def from_json(self, value):
        if not isinstance(value, str) or value[-1] != self.suffix:
            return float(value)

        return float(value[:-1])

    def from_literal(self, value):
        return self.from_json(value)


class EdmStructTypTraits(TypTraits):
    """Edm structural types (EntityType, ComplexType) traits"""

    def __init__(self, edm_type=None):
        super(EdmStructTypTraits, self).__init__()
        self._edm_type = edm_type

    # pylint: disable=no-self-use
    def to_literal(self, value):
        return EdmStructTypeSerializer.to_literal(self._edm_type, value)

    # pylint: disable=no-self-use
    def from_json(self, value):
        return EdmStructTypeSerializer.from_json(self._edm_type, value)

    def from_literal(self, value):
        return EdmStructTypeSerializer.from_literal(self._edm_type, value)


class EnumTypTrait(TypTraits):
    def __init__(self, enum_type):
        self._enum_type = enum_type

    def to_literal(self, value):
        return f'{value.parent.namespace}.{value}'

    def from_json(self, value):
        return getattr(self._enum_type, value)

    def from_literal(self, value):
        # remove namespaces
        enum_value = value.split('.')[-1]
        # remove enum type
        name = enum_value.split("'")[1]
        return getattr(self._enum_type, name)


class Typ(Identifier):
    Types = None

    Kinds = Enum('Kinds', 'Primitive Complex')

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
        return f'Collection({repr(self._item_type)})'

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
            raise PyODataException(f'Bad format: invalid list value {value}')

        return [self._item_type.traits.to_literal(v) for v in value]

    # pylint: disable=no-self-use
    def from_json(self, value):
        if not isinstance(value, list):
            raise PyODataException(f'Bad format: invalid list value {value}')

        return [self._item_type.traits.from_json(v) for v in value]


class VariableDeclaration(Identifier):
    MAXIMUM_LENGTH = -1

    def __init__(self, name, type_info, nullable, max_length, precision, scale, fixed_length=None):
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
            self._precision = 0
        else:
            self._precision = int(precision)
        if not scale:
            self._scale = 0
        else:
            self._scale = int(scale)
        self._check_scale_value()
        self._fixed_length = bool(fixed_length)

    @property
    def type_info(self):
        return self._type_info

    @property
    def typ(self):
        return self._typ

    @typ.setter
    def typ(self, value):
        if self._typ is not None:
            raise RuntimeError(f'Cannot replace {self._typ} of {self} by {value}')

        if value.name != self._type_info[1]:
            raise RuntimeError(f'{value} cannot be the type of {self}')

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

    @property
    def fixed_length(self):
        return self._fixed_length

    def from_literal(self, value):
        if value is None:
            if not self.nullable:
                raise PyODataException(f'Cannot convert null URL literal to value of {str(self)}')

            return None

        return self.typ.traits.from_literal(value)

    def to_literal(self, value):
        if value is None:
            if not self.nullable:
                raise PyODataException(f'Cannot convert None to URL literal of {str(self)}')

            return None

        return self.typ.traits.to_literal(value)

    def from_json(self, value):
        if value is None:
            if not self.nullable:
                raise PyODataException(f'Cannot convert null JSON to value of {str(self)}')

            return None

        return self.typ.traits.from_json(value)

    def to_json(self, value):
        if value is None:
            if not self.nullable:
                raise PyODataException(f'Cannot convert None to JSON of {str(self)}')

            return None

        return self.typ.traits.to_json(value)

    def _check_scale_value(self):
        if self._scale > self._precision:
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

            # generated collections for ease of lookup (e.g. function import return type)
            self._collections_entity_types = dict()
            self._collections_complex_types = dict()

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

        def add_entity_type(self, etype):
            """Add new  type to the type repository as well as its collection variant"""

            self.entity_types[etype.name] = etype

            # automatically create and register collection variant if not exists
            if isinstance(etype, NullType):
                return
            collection_type_name = f'Collection({etype.name})'
            self._collections_entity_types[collection_type_name] = Collection(etype.name, etype)
            # TODO performance memory: this is generating collection for every entity type encoutered, regardless of such collection is really used.

        def add_complex_type(self, ctype):
            """Add new complex type to the type repository as well as its collection variant"""

            self.complex_types[ctype.name] = ctype

            # automatically create and register collection variant if not exists
            if isinstance(ctype, NullType):
                return
            collection_type_name = f'Collection({ctype.name})'
            self._collections_complex_types[collection_type_name] = Collection(ctype.name, ctype)
            # TODO performance memory: this is generating collection for every entity type encoutered, regardless of such collection is really used.

        def add_enum_type(self, etype):
            """Add new enum type to the type repository"""
            self.enum_types[etype.name] = etype

    class Declarations(dict):

        def __getitem__(self, key):
            try:
                return super(Schema.Declarations, self).__getitem__(key)
            except KeyError:
                raise KeyError(f'There is no Schema Namespace {key}')

    def __init__(self, config: Config):
        super(Schema, self).__init__()

        self._decls = Schema.Declarations()
        self._config = config
        self._is_valid = False

    def __str__(self):
        return f"{self.__class__.__name__}({','.join(self.namespaces)})"

    @property
    def namespaces(self):
        return list(self._decls.keys())

    @property
    def config(self):
        return self._config

    @property
    def is_valid(self):
        """Returns if metadata provided were parsed to schema without any problem regardless of Policies (Fatal, Warning, Ignore).

        Policies affects behaviour o parser while this property represents status.
        """
        return self._is_valid

    def typ(self, type_name, namespace=None):
        """Returns either EntityType, ComplexType or EnumType that matches the name.
        """

        for type_space in (self.entity_type, self._collections_entity_types, self.complex_type, self._collections_complex_types, self.enum_type):
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
                raise KeyError(f'EntityType {type_name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.entity_types[type_name]
            except KeyError:
                pass

        raise KeyError(f'EntityType {type_name} does not exist in any Schema Namespace')

    def _collections_entity_types(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace]._collections_entity_types[type_name]
            except KeyError:
                raise KeyError(f'EntityType collection {type_name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl._collections_entity_types[type_name]
            except KeyError:
                pass

        raise KeyError(f'EntityType collection {type_name} does not exist in any Schema Namespace')

    def complex_type(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].complex_types[type_name]
            except KeyError:
                raise KeyError(f'ComplexType {type_name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.complex_types[type_name]
            except KeyError:
                pass

        raise KeyError(f'ComplexType {type_name} does not exist in any Schema Namespace')

    def _collections_complex_types(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace]._collections_complex_types[type_name]
            except KeyError:
                raise KeyError(f'ComplexType collection {type_name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl._collections_complex_types[type_name]
            except KeyError:
                pass

        raise KeyError(f'ComplexType collection {type_name} does not exist in any Schema Namespace')

    def enum_type(self, type_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].enum_types[type_name]
            except KeyError:
                raise KeyError(f'EnumType {type_name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.enum_types[type_name]
            except KeyError:
                pass

        raise KeyError(f'EnumType {type_name} does not exist in any Schema Namespace')

    def get_type(self, type_info):

        # construct search name based on collection information
        search_name = type_info.name if not type_info.is_collection else f'Collection({type_info.name})'

        # first look for type in primitive types
        try:
            return Types.from_name(search_name)
        except KeyError:
            pass

        # then look for type in entity types and collections of entity types
        try:
            return self.entity_type(search_name, type_info.namespace)
        except KeyError:
            pass

        try:
            return self._collections_entity_types(search_name, type_info.namespace)
        except KeyError:
            pass

        # then look for type in complex types and collections of complex types
        try:
            return self.complex_type(search_name, type_info.namespace)
        except KeyError:
            pass

        try:
            return self._collections_complex_types(search_name, type_info.namespace)
        except KeyError:
            pass

        # then look for type in enum types
        try:
            return self.enum_type(search_name, type_info.namespace)
        except KeyError:
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
                raise KeyError(f'EntitySet {set_name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.entity_sets[set_name]
            except KeyError:
                pass

        raise KeyError(f'EntitySet {set_name} does not exist in any Schema Namespace')

    @property
    def entity_sets(self):
        return list(itertools.chain(*(decl.list_entity_sets() for decl in list(self._decls.values()))))

    def function_import(self, function_import, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].function_imports[function_import]
            except KeyError:
                raise KeyError('FunctionImport {} does not exist in Schema Namespace {}'
                               .format(function_import, namespace))

        for decl in list(self._decls.values()):
            try:
                return decl.function_imports[function_import]
            except KeyError:
                pass

        raise KeyError(f'FunctionImport {function_import} does not exist in any Schema Namespace')

    @property
    def function_imports(self):
        return list(itertools.chain(*(decl.list_function_imports() for decl in list(self._decls.values()))))

    def association(self, association_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].associations[association_name]
            except KeyError:
                raise KeyError(f'Association {association_name} does not exist in namespace {namespace}')
        for decl in list(self._decls.values()):
            try:
                return decl.associations[association_name]
            except KeyError:
                return None

    @property
    def associations(self):
        return list(itertools.chain(*(decl.list_associations() for decl in list(self._decls.values()))))

    def association_set_by_association(self, association_name, namespace=None):
        if namespace is not None:
            for association_set in list(self._decls[namespace].association_sets.values()):
                if association_set.association_type.name == association_name:
                    return association_set
            raise KeyError('Association Set for Association {} does not exist in Schema Namespace {}'.format(
                association_name, namespace))
        for decl in list(self._decls.values()):
            for association_set in list(decl.association_sets.values()):
                if association_set.association_type.name == association_name:
                    return association_set
        raise KeyError('Association Set for Association {} does not exist in any Schema Namespace'.format(
            association_name))

    def association_set(self, set_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].association_sets[set_name]
            except KeyError:
                raise KeyError(f'Association set {set_name} does not exist in namespace {namespace}')
        for decl in list(self._decls.values()):
            try:
                return decl.association_sets[set_name]
            except KeyError:
                return None

    @property
    def association_sets(self):
        return list(itertools.chain(*(decl.list_association_sets() for decl in list(self._decls.values()))))

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
                raise PyODataModelError(f'Property {proprty} does not exist in {entity_type.name}')

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    @staticmethod
    def from_etree(schema_nodes, config: Config):
        schema = Schema(config)
        schema._is_valid = True

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
                    etype = EnumType.from_etree(enum_type, namespace, config)
                except (PyODataParserError, AttributeError) as ex:
                    config.err_policy(ParserError.ENUM_TYPE).resolve(ex)
                    etype = NullType(enum_type.get('Name'))
                    schema._is_valid = False

                decl.add_enum_type(etype)

            for complex_type in schema_node.xpath('edm:ComplexType', namespaces=config.namespaces):
                try:
                    ctype = ComplexType.from_etree(complex_type, config)
                except (KeyError, AttributeError) as ex:
                    config.err_policy(ParserError.COMPLEX_TYPE).resolve(ex)
                    ctype = NullType(complex_type.get('Name'))
                    schema._is_valid = False

                decl.add_complex_type(ctype)

            for entity_type in schema_node.xpath('edm:EntityType', namespaces=config.namespaces):
                try:
                    etype = EntityType.from_etree(entity_type, config)
                except (KeyError, AttributeError) as ex:
                    config.err_policy(ParserError.ENTITY_TYPE).resolve(ex)
                    etype = NullType(entity_type.get('Name'))
                    schema._is_valid = False

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
                        schema._is_valid = False

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

                            etype = schema.entity_type(end_role.entity_type_info.name, end_role.entity_type_info.namespace)

                            end_role.entity_type = etype
                        except KeyError:
                            schema._is_valid = False
                            raise PyODataModelError(
                                f'EntityType {end_role.entity_type_info.name} does not exist in Schema '
                                f'Namespace {end_role.entity_type_info.namespace}')

                    if assoc.referential_constraint is not None:
                        role_names = [end_role.role for end_role in assoc.end_roles]
                        principal_role = assoc.referential_constraint.principal

                        # Check if the role was defined in the current association
                        if principal_role.name not in role_names:
                            schema._is_valid = False
                            raise RuntimeError(
                                f'Role {principal_role.name} was not defined in association {assoc.name}')

                        # Check if principal role properties exist
                        role_name = principal_role.name
                        entity_type_name = assoc.end_by_role(role_name).entity_type_name
                        schema.check_role_property_names(principal_role, entity_type_name, namespace)

                        dependent_role = assoc.referential_constraint.dependent

                        # Check if the role was defined in the current association
                        if dependent_role.name not in role_names:
                            schema._is_valid = False
                            raise RuntimeError(
                                f'Role {dependent_role.name} was not defined in association {assoc.name}')

                        # Check if dependent role properties exist
                        role_name = dependent_role.name
                        entity_type_name = assoc.end_by_role(role_name).entity_type_name
                        schema.check_role_property_names(dependent_role, entity_type_name, namespace)
                except (PyODataModelError, RuntimeError) as ex:
                    config.err_policy(ParserError.ASSOCIATION).resolve(ex)
                    decl.associations[assoc.name] = NullAssociation(assoc.name)
                    schema._is_valid = False
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
                    schema._is_valid = False

        # Then, process EntitySet, FunctionImport and AssociationSet nodes.
        for schema_node in schema_nodes:
            namespace = schema_node.get('Namespace')
            decl = schema._decls[namespace]

            for entity_set in schema_node.xpath('edm:EntityContainer/edm:EntitySet', namespaces=config.namespaces):
                eset = EntitySet.from_etree(entity_set)
                eset.entity_type = schema.entity_type(eset.entity_type_info[1], namespace=eset.entity_type_info[0])
                decl.entity_sets[eset.name] = eset

            for function_import in schema_node.xpath('edm:EntityContainer/edm:FunctionImport', namespaces=config.namespaces):
                efn = FunctionImport.from_etree(function_import, config)

                # complete type information for return type and parameters
                if efn.return_type_info is not None:
                    efn.return_type = schema.get_type(efn.return_type_info)
                for param in efn.parameters:
                    param.typ = schema.get_type(param.type_info)
                decl.function_imports[efn.name] = efn

            for association_set in schema_node.xpath('edm:EntityContainer/edm:AssociationSet', namespaces=config.namespaces):
                assoc_set = AssociationSet.from_etree(association_set, config)
                try:
                    try:
                        assoc_set.association_type = schema.association(assoc_set.association_type_name,
                                                                        assoc_set.association_type_namespace)
                    except KeyError:
                        schema._is_valid = False
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
                            schema._is_valid = False
                            raise PyODataModelError('EntitySet {} does not exist in Schema Namespace {}'
                                                    .format(end.entity_set_name, namespace))
                        # Check if role is defined in Association
                        if assoc_set.association_type.end_by_role(end.role) is None:
                            schema._is_valid = False
                            raise PyODataModelError('Role {} is not defined in association {}'
                                                    .format(end.role, assoc_set.association_type_name))
                except (PyODataModelError, KeyError) as ex:
                    config.err_policy(ParserError.ASSOCIATION).resolve(ex)
                    decl.association_sets[assoc_set.name] = NullAssociation(assoc_set.name)
                    schema._is_valid = False
                else:
                    decl.association_sets[assoc_set.name] = assoc_set

        # pylint: disable=too-many-nested-blocks
        # Finally, process Annotation nodes when all Scheme nodes are completely processed.
        for schema_node in schema_nodes:
            for annotation_group in schema_node.xpath('edm:Annotations', namespaces=ANNOTATION_NAMESPACES):
                for annotation in ExternalAnnontation.from_etree(annotation_group):
                    if not annotation.element_namespace != schema.namespaces:
                        modlog().warning('{0} not in the namespaces {1}'.format(annotation, ','.join(schema.namespaces)))
                        continue

                    try:
                        if annotation.kind == Annotation.Kinds.ValueHelper:
                            try:
                                annotation.entity_set = schema.entity_set(
                                    annotation.collection_path, namespace=annotation.element_namespace)
                            except KeyError:
                                schema._is_valid = False
                                raise RuntimeError(f'Entity Set {annotation.collection_path} '
                                                   f'for {annotation} does not exist')

                            try:
                                vh_type = schema.typ(annotation.proprty_entity_type_name,
                                                     namespace=annotation.element_namespace)
                            except KeyError:
                                schema._is_valid = False
                                raise RuntimeError(f'Target Type {annotation.proprty_entity_type_name} '
                                                   f'of {annotation} does not exist')

                            try:
                                target_proprty = vh_type.proprty(annotation.proprty_name)
                            except KeyError:
                                schema._is_valid = False
                                raise RuntimeError(f'Target Property {annotation.proprty_name} '
                                                   f'of {vh_type} as defined in {annotation} does not exist')

                            annotation.proprty = target_proprty
                            target_proprty.value_helper = annotation
                    except (RuntimeError, PyODataModelError) as ex:
                        schema._is_valid = False
                        config.err_policy(ParserError.ANNOTATION).resolve(ex)

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
        return list(self._properties.values())

    def has_proprty(self, proprty_name):
        return proprty_name in self._properties

    @classmethod
    def from_etree(cls, type_node, config: Config):
        name = type_node.get('Name')
        label = sap_attribute_get_string(type_node, 'label')
        is_value_list = sap_attribute_get_bool(type_node, 'value-list', False)

        stype = cls(name, label, is_value_list)

        for proprty in type_node.xpath('edm:Property', namespaces=config.namespaces):
            stp = StructTypeProperty.from_etree(proprty)

            if stp.name in stype._properties:
                raise KeyError(f'{stype} already has property {stp.name}')

            stype._properties[stp.name] = stp

        # We have to update the property when
        # all properites are loaded because
        # there might be links between them.
        for ctp in list(stype._properties.values()):
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


class EnumMember:
    def __init__(self, parent, name, value):
        self._parent = parent
        self._name = name
        self._value = value

    def __str__(self):
        return f"{self._parent.name}\'{self._name}\'"

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def parent(self):
        return self._parent


class EnumType(Identifier):
    def __init__(self, name, is_flags, underlying_type, namespace):
        super(EnumType, self).__init__(name)
        self._member = list()
        self._underlying_type = underlying_type
        self._traits = TypTraits()
        self._namespace = namespace

        if is_flags == 'True':
            self._is_flags = True
        else:
            self._is_flags = False

    def __str__(self):
        return f"{self.__class__.__name__}({self._name})"

    def __getattr__(self, item):
        member = next(filter(lambda x: x.name == item, self._member), None)
        if member is None:
            raise PyODataException(f'EnumType {self} has no member {item}')

        return member

    def __getitem__(self, item):
        # If the item is type string then we want to check for members with that name instead
        if isinstance(item, str):
            return self.__getattr__(item)

        member = next(filter(lambda x: x.value == int(item), self._member), None)
        if member is None:
            raise PyODataException(f'EnumType {self} has no member with value {item}')

        return member

    # pylint: disable=too-many-locals
    @staticmethod
    def from_etree(type_node, namespace, config: Config):
        ename = type_node.get('Name')
        is_flags = type_node.get('IsFlags')

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

        mtype = Types.from_name(underlying_type)
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

    @property
    def is_flags(self):
        return self._is_flags

    @property
    def traits(self):
        return EnumTypTrait(self)

    @property
    def namespace(self):
        return self._namespace


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
        return self._nav_properties[property_name]

    @classmethod
    def from_etree(cls, type_node, config: Config):

        etype = super(EntityType, cls).from_etree(type_node, config)

        for proprty in type_node.xpath('edm:Key/edm:PropertyRef', namespaces=config.namespaces):
            etype._key.append(etype.proprty(proprty.get('Name')))

        for proprty in type_node.xpath('edm:NavigationProperty', namespaces=config.namespaces):
            navp = NavigationTypeProperty.from_etree(proprty)

            if navp.name in etype._nav_properties:
                raise KeyError(f'{etype} already has navigation property {navp.name}')

            etype._nav_properties[navp.name] = navp

        return etype


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
            raise RuntimeError(f'Cannot replace {self._entity_type} of {self} to {value}')

        if value.name != self.entity_type_info[1]:
            raise RuntimeError(f'{value} cannot be the type of {self}')

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

    @staticmethod
    def from_etree(entity_set_node):
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
                 sortable, filterable, filter_restr, req_in_filter, text, visible, display_format, value_list,
                 fixed_length=None):
        super(StructTypeProperty, self).__init__(name, type_info, nullable, max_length, precision, scale, fixed_length)

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
            raise RuntimeError(f'Cannot replace {self._struct_type} of {self} to {value}')

        self._struct_type = value

        if self._text_proprty_name:
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
            raise RuntimeError(f'Cannot replace value helper {self._value_helper} of {self} by {value}')

        self._value_helper = value

    @staticmethod
    def from_etree(entity_type_property_node):

        return StructTypeProperty(
            entity_type_property_node.get('Name'),
            Types.parse_type_name(entity_type_property_node.get('Type')),
            attribute_get_bool(entity_type_property_node, 'Nullable', True),
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
            sap_attribute_get_string(entity_type_property_node, 'value-list'),
            # Back to regular, non-SAP attributes.
            attribute_get_bool(entity_type_property_node, 'FixedLength', False),
        )


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
        super(NavigationTypeProperty, self).__init__(name, None, False, None, None, None, None)

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
            raise PyODataModelError(f'Cannot replace {self._association} of {self} to {value}')

        if value.name != self._association_info.name:
            raise PyODataModelError(f'{value} cannot be the type of {self}')

        self._association = value

    @property
    def to_role(self):
        return self._association.end_by_role(self.to_role_name)

    @property
    def typ(self):
        return self.to_role.entity_type

    @staticmethod
    def from_etree(node):

        return NavigationTypeProperty(
            node.get('Name'), node.get('FromRole'), node.get('ToRole'), Identifier.parse(node.get('Relationship')))


class EndRole:
    MULTIPLICITY_ONE = '1'
    MULTIPLICITY_ZERO_OR_ONE = '0..1'
    MULTIPLICITY_ZERO_OR_MORE = '*'

    def __init__(self, entity_type_info, multiplicity, role):
        self._entity_type_info = entity_type_info
        self._entity_type = None
        self._multiplicity = multiplicity
        self._role = role

    def __repr__(self):
        return f"{self.__class__.__name__}({self.role})"

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
            raise PyODataModelError(f'Cannot replace {self._entity_type} of {self} to {value}')

        if value.name != self._entity_type_info.name:
            raise PyODataModelError(f'{value} cannot be the type of {self}')

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


class ReferentialConstraintRole:
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


class ReferentialConstraint:
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
    def from_etree(referential_constraint_node, config: Config):
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
            raise RuntimeError(f'In role {principal_name} should be at least one principal property defined')

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


class Association:
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
        self._end_roles = list()

    def __str__(self):
        return f'{self.__class__.__name__}({self._name})'

    @property
    def name(self):
        return self._name

    @property
    def end_roles(self):
        return self._end_roles

    def end_by_role(self, end_role):
        try:
            return next((item for item in self._end_roles if item.role == end_role))
        except StopIteration:
            raise KeyError(f'Association {self._name} has no End with Role {end_role}')

    @property
    def referential_constraint(self):
        return self._referential_constraint

    @staticmethod
    def from_etree(association_node, config: Config):
        name = association_node.get('Name')
        association = Association(name)

        for end in association_node.xpath('edm:End', namespaces=config.namespaces):
            end_role = EndRole.from_etree(end)
            if end_role.entity_type_info is None:
                raise RuntimeError(f'End type is not specified in the association {name}')
            association._end_roles.append(end_role)

        if len(association._end_roles) != 2:
            raise RuntimeError(f'Association {name} does not have two end roles')

        refer = association_node.xpath('edm:ReferentialConstraint', namespaces=config.namespaces)
        if len(refer) > 1:
            raise RuntimeError(f'In association {name} is defined more than one referential constraint')

        if not refer:
            referential_constraint = None
        else:
            referential_constraint = ReferentialConstraint.from_etree(refer[0], config)

        association._referential_constraint = referential_constraint

        return association


class AssociationSetEndRole:
    def __init__(self, role, entity_set_name):
        self._role = role
        self._entity_set_name = entity_set_name
        self._entity_set = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.role})"

    @property
    def role(self):
        return self._role

    @property
    def entity_set_name(self):
        return self._entity_set_name

    @property
    def entity_set(self):
        return self._entity_set

    @entity_set.setter
    def entity_set(self, value):
        if self._entity_set:
            raise PyODataModelError(f'Cannot replace {self._entity_set} of {self} to {value}')

        if value.name != self._entity_set_name:
            raise PyODataModelError(
                f'Assigned entity set {value} differentiates from the declared {self._entity_set_name}')

        self._entity_set = value

    @staticmethod
    def from_etree(end_node):
        role = end_node.get('Role')
        entity_set = end_node.get('EntitySet')

        return AssociationSetEndRole(role, entity_set)


class AssociationSet:
    def __init__(self, name, association_type_name, association_type_namespace, end_roles):
        self._name = name
        self._association_type_name = association_type_name
        self._association_type_namespace = association_type_namespace
        self._association_type = None
        self._end_roles = end_roles

    def __str__(self):
        return f"{self.__class__.__name__}({self._name})"

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
    def association_type_namespace(self):
        return self._association_type_namespace

    @property
    def end_roles(self):
        return self._end_roles

    def end_by_role(self, end_role):
        try:
            return next((end for end in self._end_roles if end.role == end_role))
        except StopIteration:
            raise KeyError(f'Association set {self._name} has no End with Role {end_role}')

    def end_by_entity_set(self, entity_set):
        try:
            return next((end for end in self._end_roles if end.entity_set_name == entity_set))
        except StopIteration:
            raise KeyError(f'Association set {self._name} has no End with Entity Set {entity_set}')

    @association_type.setter
    def association_type(self, value):
        if self._association_type is not None:
            raise RuntimeError(f'Cannot replace {self._association_type} of {self} with {value}')
        self._association_type = value

    @staticmethod
    def from_etree(association_set_node, config: Config):
        end_roles = []
        name = association_set_node.get('Name')
        association = Identifier.parse(association_set_node.get('Association'))

        end_roles_list = association_set_node.xpath('edm:End', namespaces=config.namespaces)
        if len(end_roles) > 2:
            raise PyODataModelError(f'Association {name} cannot have more than 2 end roles')

        for end_role in end_roles_list:
            end_roles.append(AssociationSetEndRole.from_etree(end_role))

        return AssociationSet(name, association.name, association.namespace, end_roles)


class Annotation:
    Kinds = Enum('Kinds', 'ValueHelper')

    def __init__(self, kind, target, qualifier=None):
        super(Annotation, self).__init__()

        self._kind = kind
        self._element_namespace, self._element = target.split('.')
        self._qualifier = qualifier

    def __str__(self):
        return f"{self.__class__.__name__}({self.target})"

    @property
    def element_namespace(self):
        return self._element_namespace

    @property
    def element(self):
        return self._element

    @property
    def target(self):
        return f'{self._element_namespace}.{self._element}'

    @property
    def kind(self):
        return self._kind

    @staticmethod
    def from_etree(target, annotation_node):
        term = annotation_node.get('Term')
        if term in SAP_ANNOTATION_VALUE_LIST:
            return ValueHelper.from_etree(target, annotation_node)

        modlog().warning('Unsupported Annotation({0})'.format(term))
        return None


class ExternalAnnontation:
    @staticmethod
    def from_etree(annotations_node):
        target = annotations_node.get('Target')

        if annotations_node.get('Qualifier'):
            modlog().warning('Ignoring qualified Annotations of {}'.format(target))
            return

        for annotation in annotations_node.xpath('edm:Annotation', namespaces=ANNOTATION_NAMESPACES):
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
        return f"{self.__class__.__name__}({self.element})"

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
            raise RuntimeError(f'Cannot replace {self._proprty} of {self} with {value}')

        if value.struct_type.name != self.proprty_entity_type_name or value.name != self.proprty_name:
            raise RuntimeError(f'{self} cannot be an annotation of {value}')

        self._proprty = value

        for param in self._parameters:
            if param.local_property_name:
                etype = self._proprty.struct_type
                try:
                    param.local_property = etype.proprty(param.local_property_name)
                except KeyError:
                    raise RuntimeError('{0} of {1} points to an non existing LocalDataProperty {2} of {3}'.format(
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
            raise RuntimeError(f'Cannot replace {self._entity_set} of {self} with {value}')

        if value.name != self.collection_path:
            raise RuntimeError(f'{self} cannot be assigned to {value}')

        self._entity_set = value

        for param in self._parameters:
            if param.list_property_name:
                etype = self._entity_set.entity_type
                try:
                    param.list_property = etype.proprty(param.list_property_name)
                except KeyError:
                    raise RuntimeError('{0} of {1} points to an non existing ValueListProperty {2} of {3}'.format(
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

        raise KeyError(f'{self} has no local property {name}')

    def list_property_param(self, name):
        for prm in self._parameters:
            if prm.list_property.name == name:
                return prm

        raise KeyError(f'{self} has no list property {name}')

    @staticmethod
    def from_etree(target, annotation_node):
        label = None
        collection_path = None
        search_supported = False
        params_node = None
        for prop_value in annotation_node.xpath('edm:Record/edm:PropertyValue', namespaces=ANNOTATION_NAMESPACES):
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
            for prm in params_node.xpath('edm:Collection/edm:Record', namespaces=ANNOTATION_NAMESPACES):
                param = ValueHelperParameter.from_etree(prm)
                param.value_helper = value_helper
                value_helper._parameters.append(param)

        return value_helper


class ValueHelperParameter:
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
            return f"{self.__class__.__name__}({self._list_property_name})"

        return f"{self.__class__.__name__}({self._local_property_name}={self._list_property_name})"

    @property
    def value_helper(self):
        return self._value_helper

    @value_helper.setter
    def value_helper(self, value):
        if self._value_helper is not None:
            raise RuntimeError(f'Cannot replace {self._value_helper} of {self} with {value}')

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
            raise RuntimeError(f'Cannot replace {self._local_property} of {self} with {value}')

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
            raise RuntimeError(f'Cannot replace {self._list_property} of {self} with {value}')

        self._list_property = value

    @staticmethod
    def from_etree(value_help_parameter_node):
        typ = value_help_parameter_node.get('Type')
        direction = SAP_VALUE_HELPER_DIRECTIONS[typ]
        local_prop_name = None
        list_prop_name = None
        for pval in value_help_parameter_node.xpath('edm:PropertyValue', namespaces=ANNOTATION_NAMESPACES):
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
            raise RuntimeError(f'Cannot replace {self._return_type} of {self} by {value}')

        if value.name != self.return_type_info[1]:
            raise RuntimeError(f'{value} cannot be the type of {self}')

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

    # pylint: disable=too-many-locals
    @staticmethod
    def from_etree(function_import_node, config: Config):
        name = function_import_node.get('Name')
        entity_set = function_import_node.get('EntitySet')
        http_method = metadata_attribute_get(function_import_node, 'HttpMethod')

        rt_type = function_import_node.get('ReturnType')
        rt_info = None if rt_type is None else Types.parse_type_name(rt_type)

        parameters = dict()
        for param in function_import_node.xpath('edm:Parameter', namespaces=config.namespaces):
            param_name = param.get('Name')
            param_type_info = Types.parse_type_name(param.get('Type'))
            param_nullable = attribute_get_bool(param, 'Nullable', False)
            param_max_length = param.get('MaxLength')
            param_precision = param.get('Precision')
            param_scale = param.get('Scale')
            param_mode = param.get('Mode')

            parameters[param_name] = FunctionImportParameter(param_name, param_type_info, param_nullable,
                                                             param_max_length, param_precision, param_scale, param_mode)

        return FunctionImport(name, rt_info, entity_set, parameters, http_method)


class FunctionImportParameter(VariableDeclaration):
    Modes = Enum('Modes', 'In Out InOut')

    def __init__(self, name, type_info, nullable, max_length, precision, scale, mode):
        super(FunctionImportParameter, self).__init__(name, type_info, nullable, max_length, precision, scale, None)

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


def str_to_bool(value, attr, default):
    if value is None:
        return default

    if value == 'true':
        return True

    if value == 'false':
        return False

    raise TypeError(f'Not a bool attribute: {attr} = {value}')


def attribute_get_bool(node, attr, default):
    return str_to_bool(node.get(attr), attr, default)


def sap_attribute_get_bool(node, attr, default):
    return str_to_bool(sap_attribute_get(node, attr), attr, default)


ANNOTATION_NAMESPACES = {
    'edm': 'http://docs.oasis-open.org/odata/ns/edm',
    'edmx': 'http://docs.oasis-open.org/odata/ns/edmx'
}

SAP_VALUE_HELPER_DIRECTIONS = {
    'com.sap.vocabularies.Common.v1.ValueListParameterIn': ValueHelperParameter.Direction.In,
    'com.sap.vocabularies.Common.v1.ValueListParameterInOut': ValueHelperParameter.Direction.InOut,
    'com.sap.vocabularies.Common.v1.ValueListParameterOut': ValueHelperParameter.Direction.Out,
    'com.sap.vocabularies.Common.v1.ValueListParameterDisplayOnly': ValueHelperParameter.Direction.DisplayOnly,
    'com.sap.vocabularies.Common.v1.ValueListParameterFilterOnly': ValueHelperParameter.Direction.FilterOnly
}


SAP_ANNOTATION_VALUE_LIST = ['com.sap.vocabularies.Common.v1.ValueList']


class MetadataBuilder:
    EDMX_WHITELIST = [
        'http://schemas.microsoft.com/ado/2007/06/edmx',
        'http://docs.oasis-open.org/odata/ns/edmx',
    ]

    EDM_WHITELIST = [
        'http://schemas.microsoft.com/ado/2006/04/edm',
        'http://schemas.microsoft.com/ado/2007/05/edm',
        'http://schemas.microsoft.com/ado/2008/09/edm',
        'http://schemas.microsoft.com/ado/2009/11/edm',
        'http://docs.oasis-open.org/odata/ns/edm'
    ]

    def __init__(self, xml, config=None):
        self._xml = xml

        if config is None:
            config = Config()
        self._config = config

    @property
    def config(self):
        return self._config

    def build(self):
        """ Build model from the XML metadata"""

        if isinstance(self._xml, str):
            mdf = io.StringIO(self._xml)
        elif isinstance(self._xml, bytes):
            mdf = io.BytesIO(self._xml)
        else:
            raise TypeError(f'Expected bytes or str type on metadata_xml, got : {type(self._xml)}')

        namespaces = self._config.namespaces

        try:
            xml = etree.parse(mdf)
        except etree.XMLSyntaxError as ex:
            raise PyODataParserError('Metadata document syntax error') from ex

        edmx = xml.getroot()

        try:
            dataservices = next((child for child in edmx if etree.QName(child.tag).localname == 'DataServices'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element DataServices')

        try:
            schema = next((child for child in dataservices if etree.QName(child.tag).localname == 'Schema'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element Schema')

        if 'edmx' not in self._config.namespaces:
            namespace = etree.QName(edmx.tag).namespace

            if namespace not in self.EDMX_WHITELIST:
                raise PyODataParserError(f'Unsupported Edmx namespace - {namespace}')

            namespaces['edmx'] = namespace

        if 'edm' not in self._config.namespaces:
            namespace = etree.QName(schema.tag).namespace

            if namespace not in self.EDM_WHITELIST:
                raise PyODataParserError(f'Unsupported Schema namespace - {namespace}')

            namespaces['edm'] = namespace

        self._config.namespaces = namespaces

        self.update_global_variables_with_alias(self.get_aliases(xml, self._config))

        edm_schemas = xml.xpath('/edmx:Edmx/edmx:DataServices/edm:Schema', namespaces=self._config.namespaces)
        schema = Schema.from_etree(edm_schemas, self._config)
        return schema

    @staticmethod
    def get_aliases(edmx, config: Config):
        """Get all aliases"""

        aliases = collections.defaultdict(set)
        edm_root = edmx.xpath('/edmx:Edmx', namespaces=config.namespaces)
        if edm_root:
            edm_ref_includes = edm_root[0].xpath('edmx:Reference/edmx:Include', namespaces=ANNOTATION_NAMESPACES)
            for ref_incl in edm_ref_includes:
                namespace = ref_incl.get('Namespace')
                alias = ref_incl.get('Alias')
                if namespace is not None and alias is not None:
                    aliases[namespace].add(alias)

        return aliases

    @staticmethod
    def update_global_variables_with_alias(aliases):
        """Update global variables with aliases"""

        global SAP_ANNOTATION_VALUE_LIST  # pylint: disable=global-statement
        namespace, suffix = SAP_ANNOTATION_VALUE_LIST[0].rsplit('.', 1)
        SAP_ANNOTATION_VALUE_LIST.extend([alias + '.' + suffix for alias in aliases[namespace]])

        global SAP_VALUE_HELPER_DIRECTIONS  # pylint: disable=global-statement
        helper_direction_keys = list(SAP_VALUE_HELPER_DIRECTIONS.keys())
        for direction_key in helper_direction_keys:
            namespace, suffix = direction_key.rsplit('.', 1)
            for alias in aliases[namespace]:
                SAP_VALUE_HELPER_DIRECTIONS[alias + '.' + suffix] = SAP_VALUE_HELPER_DIRECTIONS[direction_key]


def schema_from_xml(metadata_xml, namespaces=None):
    """Parses XML data and returns Schema representing OData Metadata"""

    meta = MetadataBuilder(
        metadata_xml,
        config=Config(
            xml_namespaces=namespaces,
        ))

    return meta.build()


class Edmx:
    @staticmethod
    def parse(metadata_xml, namespaces=None):
        warnings.warn("Edmx class is deprecated in favor of MetadataBuilder", DeprecationWarning)
        return schema_from_xml(metadata_xml, namespaces)
