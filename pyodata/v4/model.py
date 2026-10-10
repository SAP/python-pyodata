"""
Simple representation of Metadata of OData V4

IDENTICAL classes are imported directly from v2.model.
V4-specific classes are written fresh.
V2-only classes (Association*, SAP value helpers, Edm.DateTime traits, ...) are omitted.
"""
# pylint: disable=missing-docstring,too-many-instance-attributes,too-many-arguments,protected-access,no-member,line-too-long,logging-format-interpolation,too-few-public-methods,too-many-lines,too-many-public-methods,unused-argument

import base64
import datetime
import io
import itertools
import logging
import re

from lxml import etree

from pyodata.exceptions import PyODataException, PyODataModelError, PyODataParserError

# Classes with zero V2/V4 differences — imported directly from v2.
# Several are re-exported for API/object-identity parity rather than used in this module.
from pyodata.v2.model import (  # pylint: disable=unused-import
    # Error policy framework
    ErrorPolicy, PolicyFatal, PolicyWarning, PolicyIgnore,
    ParserError, Config, NullType,
    # Identifier infrastructure
    Identifier, IdentifierInfo, TypeInfo,
    # Type system base
    TypTraits, EdmStructTypeSerializer, Typ, Collection,
    # Identical primitive type traits
    EdmBooleanTypTraits, EdmIntTypTraits,
    EdmStructTypTraits, EdmStringTypTraits,
    # Edm.Double/Single wire format is identical in V4 (plain FP number)
    EdmFPNumTypTraits,
    # Schema structural types (no Association refs, no SAP logic)
    StructType, EnumMember, EnumType,
    # Pure utilities
    str_to_bool, attribute_get_bool, ANNOTATION_NAMESPACES,
)

LOGGER_NAME = 'pyodata.v4.model'


def modlog():
    return logging.getLogger(LOGGER_NAME)


# ---------------------------------------------------------------------------
# V4-specific primitive type traits
# ---------------------------------------------------------------------------


class EdmDateTypTraits(TypTraits):
    """Edm.Date traits — bare 'YYYY-MM-DD' literal, ISO date JSON"""

    def to_literal(self, value):
        if isinstance(value, datetime.date):
            return value.isoformat()
        return str(value)

    def to_json(self, value):
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value

    def from_json(self, value):
        if value is None:
            return None
        return datetime.date.fromisoformat(value)

    def from_literal(self, value):
        if value is None:
            return None
        return datetime.date.fromisoformat(value)


class EdmTimeOfDayTypTraits(TypTraits):
    """Edm.TimeOfDay traits — bare 'HH:MM:SS' literal, ISO time JSON"""

    def to_literal(self, value):
        if isinstance(value, datetime.time):
            return value.isoformat()
        return str(value)

    def to_json(self, value):
        if isinstance(value, datetime.time):
            return value.isoformat()
        return value

    def from_json(self, value):
        if value is None:
            return None
        return datetime.time.fromisoformat(value)

    def from_literal(self, value):
        if value is None:
            return None
        return datetime.time.fromisoformat(value)


class EdmDurationTypTraits(TypTraits):
    """Edm.Duration traits — ISO-8601 duration, bare literal (e.g. PT1H30M)

       Supports day/hour/minute/second components only. Year/month components
       (which have no fixed length in seconds) are rejected.
    """

    # P[nD]T[nH][nM][nS]  — the whole 'T...' part is optional too (e.g. P2D)
    _PATTERN = re.compile(
        r'^(?P<sign>[+-])?P'
        r'(?:(?P<days>\d+(?:\.\d+)?)D)?'
        r'(?:T'
        r'(?:(?P<hours>\d+(?:\.\d+)?)H)?'
        r'(?:(?P<minutes>\d+(?:\.\d+)?)M)?'
        r'(?:(?P<seconds>\d+(?:\.\d+)?)S)?'
        r')?$'
    )
    # Detect year/month components which are not representable as timedelta
    _YEAR_MONTH = re.compile(r'^[+-]?P.*?\d+(?:Y|M(?![^T]*$)?)')

    def _parse(self, value):
        # Reject anything containing a year component, or a month component
        # that appears before the 'T' separator (date-part month).
        if re.search(r'\d+Y', value):
            raise PyODataException(
                f'Edm.Duration value {value} contains a year component which '
                'cannot be represented as a datetime.timedelta')
        date_part = value.split('T', 1)[0]
        if re.search(r'\d+M', date_part):
            raise PyODataException(
                f'Edm.Duration value {value} contains a month component which '
                'cannot be represented as a datetime.timedelta')

        matches = self._PATTERN.match(value)
        if not matches:
            raise PyODataException(f'Cannot parse Edm.Duration value {value}')

        sign = -1 if matches.group('sign') == '-' else 1
        days = float(matches.group('days') or 0)
        hours = float(matches.group('hours') or 0)
        minutes = float(matches.group('minutes') or 0)
        seconds = float(matches.group('seconds') or 0)

        return sign * datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    @staticmethod
    def _to_iso(value):
        if not isinstance(value, datetime.timedelta):
            return str(value)

        total = value.total_seconds()
        sign = '-' if total < 0 else ''
        total = abs(total)

        days, rem = divmod(total, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)

        result = f'{sign}P'
        if days:
            result += f'{int(days)}D'
        result += 'T'
        if hours:
            result += f'{int(hours)}H'
        if minutes:
            result += f'{int(minutes)}M'
        # Always emit seconds so the literal is never an empty 'PT'
        if seconds or (not hours and not minutes):
            if seconds == int(seconds):
                result += f'{int(seconds)}S'
            else:
                result += f'{seconds}S'
        return result

    def to_literal(self, value):
        return self._to_iso(value)

    def to_json(self, value):
        return self._to_iso(value)

    def from_json(self, value):
        if value is None:
            return None
        return self._parse(value)

    def from_literal(self, value):
        if value is None:
            return None
        return self._parse(value)


class EdmDateTimeOffsetTypTraitsV4(TypTraits):
    """Edm.DateTimeOffset traits for V4.

       V4 JSON wire format and literal form are both bare ISO-8601 strings
       (no /Date(ticks)/ JSON and no datetimeoffset'...' literal prefix).
    """

    @staticmethod
    def _parse_iso(value):
        normalized = value.strip()
        if normalized.endswith(('Z', 'z')):
            normalized = normalized[:-1] + '+00:00'
        if '.' in normalized:
            # Pad/truncate fractional seconds to 6 digits for fromisoformat
            head, rest = normalized.split('.', 1)
            tz_idx = len(rest)
            for sep in ('+', '-'):
                idx = rest.find(sep)
                if idx != -1:
                    tz_idx = min(tz_idx, idx)
            frac, tz_suffix = rest[:tz_idx], rest[tz_idx:]
            frac = frac[:6].ljust(6, '0')
            normalized = f'{head}.{frac}{tz_suffix}'
        try:
            return datetime.datetime.fromisoformat(normalized)
        except ValueError:
            raise PyODataModelError(f'Cannot decode datetimeoffset from value {value}.')

    def to_literal(self, value):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return str(value)

    def to_json(self, value):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return value

    def from_json(self, value):
        if value is None:
            return None
        return self._parse_iso(value)

    def from_literal(self, value):
        if value is None:
            return None
        return self._parse_iso(value)


class EdmInt64TypTraitsV4(TypTraits):
    """Edm.Int64 traits for V4 — plain integer (no 'L' suffix)"""

    def to_literal(self, value):
        return '%d' % (value)

    def to_json(self, value):
        return int(value)

    def from_json(self, value):
        return int(value)

    def from_literal(self, value):
        return int(value)


class EdmDecimalTypTraitsV4(TypTraits):
    """Edm.Decimal traits for V4 — plain decimal (no 'M' suffix)

       Values are passed through minimally (as str) to avoid precision loss,
       mirroring the lightweight V2 handling.
    """

    def to_literal(self, value):
        return str(value)

    def to_json(self, value):
        return value

    def from_json(self, value):
        return value

    def from_literal(self, value):
        return value


class EdmBinaryTypTraitsV4(TypTraits):
    """Edm.Binary traits for V4 — base64url encoded, no binary'...' prefix"""

    def to_literal(self, value):
        binary = base64.b64decode(value, validate=True)
        return base64.urlsafe_b64encode(binary).decode()

    def to_json(self, value):
        return value

    def from_json(self, value):
        return value

    def from_literal(self, value):
        binary = base64.urlsafe_b64decode(value)
        return base64.b64encode(binary).decode()


class EdmGuidTypTraitsV4(TypTraits):
    """Edm.Guid traits for V4 — bare UUID string, no guid'...' prefix"""

    def to_literal(self, value):
        return str(value)

    def to_json(self, value):
        return value

    def from_json(self, value):
        return value

    def from_literal(self, value):
        return value


class EdmSpatialTypTraits(TypTraits):
    """Stub for Geography/Geometry spatial types — not yet implemented"""

    def __init__(self, type_name='spatial'):
        super().__init__()
        self._type_name = type_name

    def to_literal(self, value):
        raise NotImplementedError(f'V4 spatial type {self._type_name}: to_literal not implemented')

    def to_json(self, value):
        raise NotImplementedError(f'V4 spatial type {self._type_name}: to_json not implemented')

    def from_json(self, value):
        raise NotImplementedError(f'V4 spatial type {self._type_name}: from_json not implemented')

    def from_literal(self, value):
        raise NotImplementedError(f'V4 spatial type {self._type_name}: from_literal not implemented')


class EdmStreamTypTraits(TypTraits):
    """Stub for Edm.Stream — not yet implemented"""

    def to_literal(self, value):
        raise NotImplementedError('V4 Edm.Stream: to_literal not implemented')

    def to_json(self, value):
        raise NotImplementedError('V4 Edm.Stream: to_json not implemented')

    def from_json(self, value):
        raise NotImplementedError('V4 Edm.Stream: from_json not implemented')

    def from_literal(self, value):
        raise NotImplementedError('V4 Edm.Stream: from_literal not implemented')


# ---------------------------------------------------------------------------
# V4 primitive type registry
# ---------------------------------------------------------------------------


class Types:
    """Repository of all available OData V4 primitive types + their Collection variants.

       This is a FRESH class object, independent from pyodata.v2.model.Types, so the
       V2 and V4 primitive type registries never share state.
    """

    Types = None

    # pylint: disable=too-many-statements
    @staticmethod
    def _build_types():
        """Create and register instances of all V4 primitive Edm types"""

        if Types.Types is None:
            Types.Types = {}

            Types.register_type(Typ('Null', 'null'))
            Types.register_type(Typ('Edm.Binary', '', EdmBinaryTypTraitsV4()))
            Types.register_type(Typ('Edm.Boolean', 'false', EdmBooleanTypTraits()))
            Types.register_type(Typ('Edm.Byte', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.SByte', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.Int16', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.Int32', '0', EdmIntTypTraits()))
            Types.register_type(Typ('Edm.Int64', '0', EdmInt64TypTraitsV4()))
            Types.register_type(Typ('Edm.Decimal', '0', EdmDecimalTypTraitsV4()))
            Types.register_type(Typ('Edm.Double', '0.0', EdmFPNumTypTraits.edm_double()))
            Types.register_type(Typ('Edm.Single', '0.0', EdmFPNumTypTraits.edm_single()))
            Types.register_type(Typ('Edm.String', '\'\'', EdmStringTypTraits()))
            Types.register_type(Typ('Edm.Guid', '00000000-0000-0000-0000-000000000000', EdmGuidTypTraitsV4()))
            Types.register_type(Typ('Edm.Date', '2000-01-01', EdmDateTypTraits()))
            Types.register_type(Typ('Edm.TimeOfDay', '00:00:00', EdmTimeOfDayTypTraits()))
            Types.register_type(Typ('Edm.Duration', 'PT0S', EdmDurationTypTraits()))
            Types.register_type(
                Typ('Edm.DateTimeOffset', '2000-01-01T00:00:00Z', EdmDateTimeOffsetTypTraitsV4()))
            Types.register_type(Typ('Edm.Stream', '', EdmStreamTypTraits()))
            Types.register_type(Typ('Edm.Untyped', '', TypTraits()))

            # Spatial types — registered with stub traits (methods raise NotImplementedError)
            spatial_names = [
                'Point', 'LineString', 'Polygon', 'MultiPoint',
                'MultiLineString', 'MultiPolygon', 'GeometryCollection',
            ]
            for prefix in ('Geography', 'Geometry'):
                for name in spatial_names:
                    full = f'Edm.{prefix}{name}'
                    Types.register_type(Typ(full, '', EdmSpatialTypTraits(full)))

    @staticmethod
    def register_type(typ):
        """Add new type to the type repository as well as its collection variant"""

        if Types.Types is None:
            Types._build_types()

        # pylint: disable=unsupported-membership-test
        if typ.name not in Types.Types:
            # pylint: disable=unsupported-assignment-operation
            Types.Types[typ.name] = typ

        collection_name = f'Collection({typ.name})'
        # pylint: disable=unsupported-membership-test
        if collection_name not in Types.Types:
            collection_typ = Collection(typ.name, typ)
            # pylint: disable=unsupported-assignment-operation
            Types.Types[collection_name] = collection_typ

    @staticmethod
    def from_name(name):

        if Types.Types is None:
            Types._build_types()

        search_name = name

        is_collection = name.lower().startswith('collection(') and name.endswith(')')
        if is_collection:
            name = name[11:-1]
            search_name = f'Collection({name})'

        # pylint: disable=unsubscriptable-object
        return Types.Types[search_name]

    @staticmethod
    def parse_type_name(type_name):

        is_collection = type_name.lower().startswith('collection(') and type_name.endswith(')')
        if is_collection:
            type_name = type_name[11:-1]

        identifier = Identifier.parse(type_name)

        if identifier.namespace == 'Edm':
            return TypeInfo(None, type_name, is_collection)

        return TypeInfo(identifier.namespace, identifier.name, is_collection)


# ---------------------------------------------------------------------------
# Variable declarations and struct properties
# ---------------------------------------------------------------------------


class VariableDeclaration(Identifier):
    MAXIMUM_LENGTH = -1

    def __init__(self, name, type_info, nullable, max_length, precision, scale):
        super().__init__(name)

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

        # V4 allows Scale='variable' (and 'floating')
        if scale is None or scale == '':
            self._scale = 0
        elif isinstance(scale, str) and scale.lower() in ('variable', 'floating'):
            self._scale = scale.lower()
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
        # 'variable'/'floating' scale is not subject to the numeric comparison
        if isinstance(self._scale, str):
            return
        if self._scale > self._precision:
            raise PyODataModelError('Scale value ({}) must be less than or equal to precision value ({})'
                                    .format(self._scale, self._precision))


class StructTypeProperty(VariableDeclaration):
    """Property of structure types (Entity/Complex type) for OData V4.

       V4 removes fixed_length and all SAP-specific attributes. The type of
       the property can be a primitive type, complex type, enumeration type
       or a collection of one of these.
    """

    def __init__(self, name, type_info, nullable, max_length, precision, scale):
        super().__init__(name, type_info, nullable, max_length, precision, scale)

        self._struct_type = None
        self._value_helper = None

    @property
    def struct_type(self):
        return self._struct_type

    @struct_type.setter
    def struct_type(self, value):
        if self._struct_type is not None:
            raise RuntimeError(f'Cannot replace {self._struct_type} of {self} to {value}')
        self._struct_type = value

    @property
    def value_helper(self):
        # V4 does not parse SAP value helpers; kept so downstream code is safe.
        return self._value_helper

    @staticmethod
    def from_etree(entity_type_property_node):
        return StructTypeProperty(
            entity_type_property_node.get('Name'),
            Types.parse_type_name(entity_type_property_node.get('Type')),
            attribute_get_bool(entity_type_property_node, 'Nullable', True),
            entity_type_property_node.get('MaxLength'),
            entity_type_property_node.get('Precision'),
            entity_type_property_node.get('Scale'),
        )


# ---------------------------------------------------------------------------
# Navigation property (V4 semantics)
# ---------------------------------------------------------------------------


class NavigationTypeProperty(Identifier):
    """V4 navigation property.

       Unlike V2 (which refers to an Association via FromRole/ToRole), a V4
       navigation property declares its target type inline via Type=, an
       optional Partner=, and an optional ContainsTarget= for containment.
    """

    def __init__(self, name, type_info, partner=None, contains_target=False, nullable=True):
        super().__init__(name)

        self._type_info = type_info
        self._partner = partner
        self._contains_target = contains_target
        self._nullable = nullable
        self._typ = None

    @property
    def type_info(self):
        return self._type_info

    @property
    def partner(self):
        return self._partner

    @property
    def contains_target(self):
        return self._contains_target

    @property
    def nullable(self):
        return self._nullable

    @property
    def typ(self):
        return self._typ

    @typ.setter
    def typ(self, value):
        self._typ = value

    @staticmethod
    def from_etree(node, config):
        return NavigationTypeProperty(
            node.get('Name'),
            Types.parse_type_name(node.get('Type')),
            partner=node.get('Partner'),
            contains_target=attribute_get_bool(node, 'ContainsTarget', False),
            nullable=attribute_get_bool(node, 'Nullable', True),
        )


# ---------------------------------------------------------------------------
# Structural types with V4 parsing
# ---------------------------------------------------------------------------


class ComplexType(StructType):
    """Representation of Edm.ComplexType for V4 (allows navigation properties)"""

    def __init__(self, name, label=None, is_value_list=False):
        super().__init__(name, label, is_value_list)
        self._nav_properties = dict()
        self._base_type = None
        self._open_type = False
        self._abstract = False

    @property
    def base_type(self):
        return self._base_type

    @property
    def open_type(self):
        return self._open_type

    @property
    def abstract(self):
        return self._abstract

    @property
    def nav_proprties(self):
        return list(self._nav_properties.values())

    def nav_proprty(self, property_name):
        return self._nav_properties[property_name]

    @classmethod
    def from_etree(cls, type_node, config: Config):
        name = type_node.get('Name')
        stype = cls(name)
        stype._base_type = type_node.get('BaseType')
        stype._open_type = attribute_get_bool(type_node, 'OpenType', False)
        stype._abstract = attribute_get_bool(type_node, 'Abstract', False)

        for proprty in type_node.xpath('edm:Property', namespaces=config.namespaces):
            stp = StructTypeProperty.from_etree(proprty)
            if stp.name in stype._properties:
                raise KeyError(f'{stype} already has property {stp.name}')
            stype._properties[stp.name] = stp

        for ctp in list(stype._properties.values()):
            ctp.struct_type = stype

        for nav in type_node.xpath('edm:NavigationProperty', namespaces=config.namespaces):
            navp = NavigationTypeProperty.from_etree(nav, config)
            if navp.name in stype._nav_properties:
                raise KeyError(f'{stype} already has navigation property {navp.name}')
            stype._nav_properties[navp.name] = navp

        return stype


class EntityType(StructType):
    """Representation of Edm.EntityType for V4"""

    def __init__(self, name, label=None, is_value_list=False):
        super().__init__(name, label, is_value_list)
        self._key = list()
        self._nav_properties = dict()
        self._base_type = None
        self._open_type = False
        self._abstract = False

    @property
    def key_proprties(self):
        return list(self._key)

    @property
    def base_type(self):
        return self._base_type

    @property
    def open_type(self):
        return self._open_type

    @property
    def abstract(self):
        return self._abstract

    @property
    def nav_proprties(self):
        """Gets the navigation properties defined for this entity type"""
        return list(self._nav_properties.values())

    def nav_proprty(self, property_name):
        return self._nav_properties[property_name]

    @classmethod
    def from_etree(cls, type_node, config: Config):
        name = type_node.get('Name')
        etype = cls(name)
        etype._base_type = type_node.get('BaseType')
        etype._open_type = attribute_get_bool(type_node, 'OpenType', False)
        etype._abstract = attribute_get_bool(type_node, 'Abstract', False)

        for proprty in type_node.xpath('edm:Property', namespaces=config.namespaces):
            stp = StructTypeProperty.from_etree(proprty)
            if stp.name in etype._properties:
                raise KeyError(f'{etype} already has property {stp.name}')
            etype._properties[stp.name] = stp

        for ctp in list(etype._properties.values()):
            ctp.struct_type = etype

        for proprty in type_node.xpath('edm:Key/edm:PropertyRef', namespaces=config.namespaces):
            if proprty.get('Alias') is not None:
                raise NotImplementedError(
                    'V4 key aliases (PropertyRef/@Alias) are not yet supported for URL generation')
            etype._key.append(etype.proprty(proprty.get('Name')))

        for nav in type_node.xpath('edm:NavigationProperty', namespaces=config.namespaces):
            navp = NavigationTypeProperty.from_etree(nav, config)
            if navp.name in etype._nav_properties:
                raise KeyError(f'{etype} already has navigation property {navp.name}')
            etype._nav_properties[navp.name] = navp

        return etype


class EntitySet(Identifier):
    """V4 EntitySet — no SAP attributes; carries NavigationPropertyBindings"""

    def __init__(self, name, entity_type_info, navigation_property_bindings=None):
        super().__init__(name)

        self._entity_type_info = entity_type_info
        self._entity_type = None
        self._navigation_property_bindings = navigation_property_bindings or []

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
    def navigation_property_bindings(self):
        return self._navigation_property_bindings

    @staticmethod
    def from_etree(node, config: Config):
        name = node.get('Name')
        et_info = Types.parse_type_name(node.get('EntityType'))

        bindings = []
        for binding in node.xpath('edm:NavigationPropertyBinding', namespaces=config.namespaces):
            bindings.append((binding.get('Path'), binding.get('Target')))

        return EntitySet(name, et_info, bindings)


# ---------------------------------------------------------------------------
# V4-only schema members: Singleton, Action, Function, imports
# ---------------------------------------------------------------------------


class ParameterDeclaration(VariableDeclaration):
    """A single Action/Function parameter"""

    def __init__(self, name, type_info, nullable=True, max_length=None, precision=None, scale=None):
        super().__init__(name, type_info, nullable, max_length, precision, scale)

    @staticmethod
    def from_etree(node):
        return ParameterDeclaration(
            node.get('Name'),
            Types.parse_type_name(node.get('Type')),
            attribute_get_bool(node, 'Nullable', True),
            node.get('MaxLength'),
            node.get('Precision'),
            node.get('Scale'),
        )


class Singleton(Identifier):
    """V4 Singleton — a single named entity with no key predicate"""

    def __init__(self, name, entity_type_info, navigation_property_bindings=None):
        super().__init__(name)

        self._entity_type_info = entity_type_info
        self._entity_type = None
        self._navigation_property_bindings = navigation_property_bindings or []

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
        self._entity_type = value

    @property
    def navigation_property_bindings(self):
        return self._navigation_property_bindings

    @staticmethod
    def from_etree(node, config: Config):
        name = node.get('Name')
        et_info = Types.parse_type_name(node.get('Type'))

        bindings = []
        for binding in node.xpath('edm:NavigationPropertyBinding', namespaces=config.namespaces):
            bindings.append((binding.get('Path'), binding.get('Target')))

        return Singleton(name, et_info, bindings)


class _OperationBase(Identifier):
    """Shared implementation for V4 Action and Function"""

    def __init__(self, name, is_bound, binding_parameter_type, parameters, return_type_info):
        super().__init__(name)

        self._is_bound = is_bound
        self._binding_parameter_type = binding_parameter_type
        self._parameters = parameters
        self._return_type_info = return_type_info
        self._return_type = None

    @property
    def is_bound(self):
        return self._is_bound

    @property
    def binding_parameter_type(self):
        return self._binding_parameter_type

    @property
    def parameters(self):
        return list(self._parameters.values())

    def get_parameter(self, name):
        return self._parameters[name]

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
        self._return_type = value

    @classmethod
    def from_etree(cls, node, config: Config):
        name = node.get('Name')
        is_bound = attribute_get_bool(node, 'IsBound', False)

        parameters = dict()
        binding_parameter_type = None
        for idx, param in enumerate(node.xpath('edm:Parameter', namespaces=config.namespaces)):
            decl = ParameterDeclaration.from_etree(param)
            parameters[decl.name] = decl
            # For bound operations, the first parameter is the binding parameter.
            if is_bound and idx == 0:
                binding_parameter_type = decl.type_info

        return_type_info = None
        rt_nodes = node.xpath('edm:ReturnType', namespaces=config.namespaces)
        if rt_nodes:
            rt_type = rt_nodes[0].get('Type')
            if rt_type is not None:
                return_type_info = Types.parse_type_name(rt_type)
        elif node.get('ReturnType') is not None:
            return_type_info = Types.parse_type_name(node.get('ReturnType'))

        return cls(name, is_bound, binding_parameter_type, parameters, return_type_info)


class Action(_OperationBase):
    """V4 Action — a (possibly bound) operation with side effects"""


class Function(_OperationBase):
    """V4 Function — a (possibly bound) operation without side effects"""


class ActionImport(Identifier):
    """V4 ActionImport — exposes an Action in the entity container"""

    def __init__(self, name, action_name, entity_set=None):
        super().__init__(name)

        self._action_name = action_name
        self._entity_set_name = entity_set
        self._action = None

    @property
    def action_name(self):
        return self._action_name

    @property
    def entity_set_name(self):
        return self._entity_set_name

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, value):
        self._action = value

    @property
    def parameters(self):
        if self._action is None:
            return []
        return self._action.parameters

    @property
    def return_type_info(self):
        return None if self._action is None else self._action.return_type_info

    @property
    def return_type(self):
        return None if self._action is None else self._action.return_type

    @staticmethod
    def from_etree(node, config: Config):
        return ActionImport(
            node.get('Name'),
            node.get('Action'),
            node.get('EntitySet'),
        )


# ---------------------------------------------------------------------------
# FunctionImport for V4
# ---------------------------------------------------------------------------


class FunctionImport(Identifier):
    """V4 FunctionImport — references a Function via Function=; no http_method"""

    def __init__(self, name, function_name, entity_set=None):
        super().__init__(name)

        self._function_name = function_name
        self._entity_set_name = entity_set
        self._function = None

    @property
    def function_name(self):
        return self._function_name

    @property
    def entity_set_name(self):
        return self._entity_set_name

    @property
    def function(self):
        return self._function

    @function.setter
    def function(self, value):
        self._function = value

    @property
    def parameters(self):
        if self._function is None:
            return []
        return self._function.parameters

    @property
    def return_type_info(self):
        return None if self._function is None else self._function.return_type_info

    @property
    def return_type(self):
        return None if self._function is None else self._function.return_type

    @staticmethod
    def from_etree(node, config: Config):
        return FunctionImport(
            node.get('Name'),
            node.get('Function'),
            node.get('EntitySet'),
        )


# ---------------------------------------------------------------------------
# Schema for V4
# ---------------------------------------------------------------------------


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
            self.singletons = dict()
            self.action_imports = dict()
            self.functions = dict()
            self.actions = dict()

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

        def list_singletons(self):
            return list(self.singletons.values())

        def list_action_imports(self):
            return list(self.action_imports.values())

        def list_functions(self):
            return list(self.functions.values())

        def list_actions(self):
            return list(self.actions.values())

        def add_entity_type(self, etype):
            self.entity_types[etype.name] = etype
            if isinstance(etype, NullType):
                return
            collection_type_name = f'Collection({etype.name})'
            self._collections_entity_types[collection_type_name] = Collection(etype.name, etype)

        def add_complex_type(self, ctype):
            self.complex_types[ctype.name] = ctype
            if isinstance(ctype, NullType):
                return
            collection_type_name = f'Collection({ctype.name})'
            self._collections_complex_types[collection_type_name] = Collection(ctype.name, ctype)

        def add_enum_type(self, etype):
            self.enum_types[etype.name] = etype

    class Declarations(dict):

        def __getitem__(self, key):
            try:
                return super(Schema.Declarations, self).__getitem__(key)
            except KeyError:
                raise KeyError(f'There is no Schema Namespace {key}')

    def __init__(self, config: Config):
        super().__init__()

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
        return self._is_valid

    def typ(self, type_name, namespace=None):
        """Returns either EntityType, ComplexType or EnumType that matches the name."""

        for type_space in (self.entity_type, self._collections_entity_types, self.complex_type,
                           self._collections_complex_types, self.enum_type):
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

        search_name = type_info.name if not type_info.is_collection else f'Collection({type_info.name})'

        try:
            return Types.from_name(search_name)
        except KeyError:
            pass

        try:
            return self.entity_type(search_name, type_info.namespace)
        except KeyError:
            pass

        try:
            return self._collections_entity_types(search_name, type_info.namespace)
        except KeyError:
            pass

        try:
            return self.complex_type(search_name, type_info.namespace)
        except KeyError:
            pass

        try:
            return self._collections_complex_types(search_name, type_info.namespace)
        except KeyError:
            pass

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

    def entity_set_for_type(self, entity_type_name):
        """Return the first entity set whose entity type matches the given name."""
        for eset in self.entity_sets:
            if eset.entity_type is not None and eset.entity_type.name == entity_type_name:
                return eset
        raise KeyError(f'No EntitySet found for EntityType {entity_type_name}')

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

    def singleton(self, name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].singletons[name]
            except KeyError:
                raise KeyError(f'Singleton {name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.singletons[name]
            except KeyError:
                pass

        raise KeyError(f'Singleton {name} does not exist in any Schema Namespace')

    @property
    def singletons(self):
        return list(itertools.chain(*(decl.list_singletons() for decl in list(self._decls.values()))))

    def action_import(self, name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].action_imports[name]
            except KeyError:
                raise KeyError(f'ActionImport {name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.action_imports[name]
            except KeyError:
                pass

        raise KeyError(f'ActionImport {name} does not exist in any Schema Namespace')

    @property
    def action_imports(self):
        return list(itertools.chain(*(decl.list_action_imports() for decl in list(self._decls.values()))))

    def function(self, name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].functions[name]
            except KeyError:
                raise KeyError(f'Function {name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.functions[name]
            except KeyError:
                pass

        raise KeyError(f'Function {name} does not exist in any Schema Namespace')

    @property
    def functions(self):
        return list(itertools.chain(*(decl.list_functions() for decl in list(self._decls.values()))))

    def action(self, name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].actions[name]
            except KeyError:
                raise KeyError(f'Action {name} does not exist in Schema Namespace {namespace}')

        for decl in list(self._decls.values()):
            try:
                return decl.actions[name]
            except KeyError:
                pass

        raise KeyError(f'Action {name} does not exist in any Schema Namespace')

    @property
    def actions(self):
        return list(itertools.chain(*(decl.list_actions() for decl in list(self._decls.values()))))

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-nested-blocks
    @staticmethod
    def from_etree(schema_nodes, config: Config):
        schema = Schema(config)
        schema._is_valid = True

        # Pass 1: EnumType, ComplexType, EntityType (minimal cross-references)
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

        # Resolve property types
        for stype in itertools.chain(schema.entity_types, schema.complex_types):
            if isinstance(stype, NullType):
                continue
            if stype.kind == Typ.Kinds.Complex:
                if stype.is_collection:
                    continue
                for prop in stype.proprties():
                    try:
                        prop.typ = schema.get_type(prop.type_info)
                    except PyODataModelError as ex:
                        config.err_policy(ParserError.PROPERTY).resolve(ex)
                        prop.typ = NullType(prop.type_info.name)
                        schema._is_valid = False

        # Resolve navigation property target types (V4: directly from Type=)
        for stype in itertools.chain(schema.entity_types, schema.complex_types):
            if isinstance(stype, NullType) or stype.is_collection:
                continue
            if not hasattr(stype, 'nav_proprties'):
                continue
            for nav_prop in stype.nav_proprties:
                try:
                    nav_prop.typ = schema.get_type(nav_prop.type_info)
                except (PyODataModelError, KeyError) as ex:
                    config.err_policy(ParserError.PROPERTY).resolve(ex)
                    nav_prop.typ = NullType(nav_prop.type_info.name)
                    schema._is_valid = False

        # Pass 2: container members + unbound Functions/Actions
        for schema_node in schema_nodes:
            namespace = schema_node.get('Namespace')
            decl = schema._decls[namespace]

            for function in schema_node.xpath('edm:Function', namespaces=config.namespaces):
                func = Function.from_etree(function, config)
                decl.functions[func.name] = func

            for action in schema_node.xpath('edm:Action', namespaces=config.namespaces):
                act = Action.from_etree(action, config)
                decl.actions[act.name] = act

            for entity_set in schema_node.xpath('edm:EntityContainer/edm:EntitySet', namespaces=config.namespaces):
                eset = EntitySet.from_etree(entity_set, config)
                try:
                    eset.entity_type = schema.entity_type(eset.entity_type_info[1], namespace=eset.entity_type_info[0])
                except KeyError as ex:
                    config.err_policy(ParserError.ENTITY_TYPE).resolve(ex)
                    schema._is_valid = False
                decl.entity_sets[eset.name] = eset

            for singleton in schema_node.xpath('edm:EntityContainer/edm:Singleton', namespaces=config.namespaces):
                sgl = Singleton.from_etree(singleton, config)
                try:
                    sgl.entity_type = schema.entity_type(sgl.entity_type_info[1], namespace=sgl.entity_type_info[0])
                except KeyError as ex:
                    config.err_policy(ParserError.ENTITY_TYPE).resolve(ex)
                    schema._is_valid = False
                decl.singletons[sgl.name] = sgl

            for function_import in schema_node.xpath('edm:EntityContainer/edm:FunctionImport', namespaces=config.namespaces):
                efn = FunctionImport.from_etree(function_import, config)
                decl.function_imports[efn.name] = efn

            for action_import in schema_node.xpath('edm:EntityContainer/edm:ActionImport', namespaces=config.namespaces):
                aim = ActionImport.from_etree(action_import, config)
                decl.action_imports[aim.name] = aim

        # Resolve Function/Action return types and parameter types
        for func in itertools.chain(schema.functions, schema.actions):
            if func.return_type_info is not None:
                try:
                    func.return_type = schema.get_type(func.return_type_info)
                except PyODataModelError as ex:
                    config.err_policy(ParserError.PROPERTY).resolve(ex)
                    schema._is_valid = False
            for param in func.parameters:
                try:
                    param.typ = schema.get_type(param.type_info)
                except PyODataModelError as ex:
                    config.err_policy(ParserError.PROPERTY).resolve(ex)
                    param.typ = NullType(param.type_info.name)
                    schema._is_valid = False

        # Resolve FunctionImport -> Function
        for efn in schema.function_imports:
            if efn.function_name is None:
                continue
            fqn = Identifier.parse(efn.function_name)
            try:
                efn.function = schema.function(fqn.name, namespace=fqn.namespace)
            except KeyError as ex:
                config.err_policy(ParserError.PROPERTY).resolve(ex)
                schema._is_valid = False

        # Resolve ActionImport -> Action
        for aim in schema.action_imports:
            if aim.action_name is None:
                continue
            fqn = Identifier.parse(aim.action_name)
            try:
                aim.action = schema.action(fqn.name, namespace=fqn.namespace)
            except KeyError as ex:
                config.err_policy(ParserError.PROPERTY).resolve(ex)
                schema._is_valid = False

        return schema


# ---------------------------------------------------------------------------
# MetadataBuilder for V4
# ---------------------------------------------------------------------------


class MetadataBuilder:
    """Builds a V4 Schema from EDMX metadata XML."""

    EDMX_WHITELIST = ['http://docs.oasis-open.org/odata/ns/edmx']
    EDM_WHITELIST = ['http://docs.oasis-open.org/odata/ns/edm']

    SUPPORTED_VERSIONS = ('4.0', '4.01')

    def __init__(self, xml, config=None):
        self._xml = xml

        if config is None:
            config = Config()
        self._config = config

        self.reference_uris = []

    @property
    def config(self):
        return self._config

    def build(self):
        """Build model from the XML metadata"""

        match self._xml:
            case str():
                mdf = io.StringIO(self._xml)
            case bytes():
                mdf = io.BytesIO(self._xml)
            case _:
                raise TypeError(f'Expected bytes or str type on metadata_xml, got : {type(self._xml)}')

        namespaces = self._config.namespaces

        try:
            xml = etree.parse(mdf)
        except etree.XMLSyntaxError as ex:
            raise PyODataParserError('Metadata document syntax error') from ex

        edmx = xml.getroot()

        version = edmx.get('Version')
        if version not in self.SUPPORTED_VERSIONS:
            raise PyODataParserError(
                f'Unsupported OData version - expected one of {self.SUPPORTED_VERSIONS}, got {version!r}')

        try:
            dataservices = next((child for child in edmx if etree.QName(child.tag).localname == 'DataServices'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element DataServices')

        try:
            schema_node = next((child for child in dataservices if etree.QName(child.tag).localname == 'Schema'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element Schema')

        if 'edmx' not in self._config.namespaces:
            namespace = etree.QName(edmx.tag).namespace
            if namespace not in self.EDMX_WHITELIST:
                raise PyODataParserError(f'Unsupported Edmx namespace - {namespace}')
            namespaces['edmx'] = namespace

        if 'edm' not in self._config.namespaces:
            namespace = etree.QName(schema_node.tag).namespace
            if namespace not in self.EDM_WHITELIST:
                raise PyODataParserError(f'Unsupported Schema namespace - {namespace}')
            namespaces['edm'] = namespace

        self._config.namespaces = namespaces

        # Collect references but do NOT fetch them (out of scope for Phase A).
        for ref in xml.xpath('/edmx:Edmx/edmx:Reference', namespaces=self._config.namespaces):
            uri = ref.get('Uri')
            if uri is not None:
                self.reference_uris.append(uri)
                modlog().debug('Found edmx:Reference Uri=%s (not fetched)', uri)

        edm_schemas = xml.xpath('/edmx:Edmx/edmx:DataServices/edm:Schema', namespaces=self._config.namespaces)
        return Schema.from_etree(edm_schemas, self._config)


def schema_from_xml(metadata_xml, namespaces=None):
    """Parses XML data and returns a V4 Schema representing OData Metadata"""

    meta = MetadataBuilder(
        metadata_xml,
        config=Config(
            xml_namespaces=namespaces,
        ))

    return meta.build()
