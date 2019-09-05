# pylint: disable=missing-docstring

import datetime
import re

from pyodata.exceptions import PyODataException, PyODataModelError


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
            raise PyODataException('Cannot encode value {} without complex type information'.format(value))

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.typ.traits.to_literal(value[type_prop.name])

        return result

    @staticmethod
    def from_json(edm_type, value):

        # pylint: disable=no-self-use
        if not edm_type:
            raise PyODataException('Cannot decode value {} without complex type information'.format(value))

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.typ.traits.from_json(value[type_prop.name])

        return result

    @staticmethod
    def from_literal(edm_type, value):

        # pylint: disable=no-self-use
        if not edm_type:
            raise PyODataException('Cannot decode value {} without complex type information'.format(value))

        result = {}
        for type_prop in edm_type.proprties():
            if type_prop.name in value:
                result[type_prop.name] = type_prop.typ.traits.from_literal(value[type_prop.name])

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
        matches = re.match("^{}'(.*)'$".format(self._prefix), value)
        if not matches:
            raise PyODataModelError(
                "Malformed value {0} for primitive Edm type. Expected format is {1}'value'".format(value, self._prefix))
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
                'Cannot convert value of type {} to literal. Datetime format is required.'.format(type(value)))

        return super(EdmDateTimeTypTraits, self).to_literal(value.replace(tzinfo=None).isoformat())

    def to_json(self, value):
        if isinstance(value, str):
            return value

        # Converts datetime into timestamp in milliseconds in UTC timezone as defined in ODATA specification
        # https://www.odata.org/documentation/odata-version-2-0/json-format/
        return f'/Date({int(value.replace(tzinfo=datetime.timezone.utc).timestamp()) * 1000})/'

    def from_json(self, value):

        if value is None:
            return None

        matches = re.match(r"^/Date\((.*)\)/$", value)
        if not matches:
            raise PyODataModelError(
                "Malformed value {0} for primitive Edm type. Expected format is /Date(value)/".format(value))
        value = matches.group(1)

        try:
            # https://stackoverflow.com/questions/36179914/timestamp-out-of-range-for-platform-localtime-gmtime-function
            value = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(
                milliseconds=int(value))
        except ValueError:
            raise PyODataModelError('Cannot decode datetime from value {}.'.format(value))

        return value

    def from_literal(self, value):

        if value is None:
            return None

        value = super(EdmDateTimeTypTraits, self).from_literal(value)

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
        return EdmStructTypeSerializer.from_json(self._edm_type, value)


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
