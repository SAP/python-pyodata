""" Type traits for types specific to the ODATA V4"""

import datetime

# In case you want to use geojson types. You have to install pip package 'geojson'
from collections import namedtuple

try:
    import geojson
    GEOJSON_MODULE = True
except ImportError:
    GEOJSON_MODULE = False

from pyodata.exceptions import PyODataModelError, PyODataException
from pyodata.model.type_traits import TypTraits


class EdmDoubleQuotesEncapsulatedTypTraits(TypTraits):
    """Good for all types which are encapsulated in double quotes"""

    def to_literal(self, value):
        return '\"%s\"' % (value)

    def to_json(self, value):
        return self.to_literal(value)

    def from_literal(self, value):
        return value.strip('\"')

    def from_json(self, value):
        return self.from_literal(value)


class EdmDateTypTraits(EdmDoubleQuotesEncapsulatedTypTraits):
    """Emd.Date traits
        Date is new type in ODATA V4. According to found resources the literal and json form is unified and is
        complaint with iso format.

        http://docs.oasis-open.org/odata/odata/v4.0/errata02/os/complete/part3-csdl/odata-v4.0-errata02-os-part3-csdl-complete.html#_Toc406397943
        https://www.w3.org/TR/2012/REC-xmlschema11-2-20120405/#date
    """

    def to_literal(self, value: datetime.date):
        if not isinstance(value, datetime.date):
            raise PyODataModelError(
                'Cannot convert value of type {} to literal. Date format is required.'.format(type(value)))

        return super().to_literal(value.isoformat())

    def to_json(self, value: datetime.date):
        return self.to_literal(value)

    def from_literal(self, value: str):
        if value is None:
            return None

        try:
            return datetime.date.fromisoformat(super().from_literal(value))
        except ValueError:
            raise PyODataModelError('Cannot decode date from value {}.'.format(value))

    def from_json(self, value: str):
        return self.from_literal(value)


class EdmTimeOfDay(EdmDoubleQuotesEncapsulatedTypTraits):
    """ Emd.TimeOfDay traits

        Represents time without timezone information
        JSON and literal format: "hh:mm:ss.s"

        JSON example:
        "TimeOfDayValue": "07:59:59.999"
    """

    def to_literal(self, value: datetime.time):
        if not isinstance(value, datetime.time):
            raise PyODataModelError(
                'Cannot convert value of type {} to literal. Time format is required.'.format(type(value)))

        return super().to_literal(value.replace(tzinfo=None).isoformat())

    def to_json(self, value: datetime.time):
        return self.to_literal(value)

    def from_literal(self, value: str):
        if value is None:
            return None

        try:
            return datetime.time.fromisoformat(super().from_literal(value))
        except ValueError:
            raise PyODataModelError('Cannot decode date from value {}.'.format(value))

    def from_json(self, value: str):
        return self.from_literal(value)


class EdmDuration(TypTraits):
    """ Emd.Duration traits

        Represents time duration as described in xml specification (https://www.w3.org/TR/xmlschema11-2/#duration)
        JSON and literal format is variable e. g.
        - P2Y6M5DT12H35M30S => 2 years, 6 months, 5 days, 12 hours, 35 minutes, 30 seconds
        - P1DT2H => 1 day, 2 hours

        http://www.datypic.com/sc/xsd/t-xsd_duration.html

        As python has no native way to represent duration we simply return int which represents duration in seconds
        For more advance operations with duration you can use datetimeutils module from pip
    """

    Duration = namedtuple('Duration', 'year month day hour minute second')

    def to_literal(self, value: Duration) -> str:
        result = 'P'

        if not isinstance(value, EdmDuration.Duration):
            raise PyODataModelError(f'Cannot convert value of type {type(value)}. Duration format is required.')

        if value.year > 0:
            result += f'{value.year}Y'

        if value.month > 0:
            result += f'{value.month}M'

        if value.day > 0:
            result += f'{value.day}D'

        if value.hour > 0 or value.minute > 0 or value.second > 0:
            result += 'T'

        if value.hour:
            result += f'{value.hour}H'

        if value.minute > 0:
            result += f'{value.minute}M'

        if value.second > 0:
            result += f'{value.second}S'

        return result

    def to_json(self, value: Duration) -> str:
        return self.to_literal(value)

    def from_literal(self, value: str) -> 'Duration':
        value = value[1:]
        time_part = False
        offset = 0
        year, month, day, hour, minute, second = 0, 0, 0, 0, 0, 0

        for index, char in enumerate(value):
            if char == 'T':
                offset += 1
                time_part = True
            elif char.isalpha():
                count = int(value[offset:index])

                if char == 'Y':
                    year = count
                elif char == 'M' and not time_part:
                    month = count
                elif char == 'D':
                    day = count
                elif char == 'H':
                    hour = count
                elif char == 'M':
                    minute = count
                elif char == 'S':
                    second = count

                offset = index + 1

        return EdmDuration.Duration(year, month, day, hour, minute, second)

    def from_json(self, value: str) -> 'Duration':
        return self.from_literal(value)


class EdmDateTimeOffsetTypTraits(EdmDoubleQuotesEncapsulatedTypTraits):
    """ Emd.DateTimeOffset traits

        Represents date and time with timezone information
        JSON and literal format: " YYYY-MM-DDThh:mm:ss.sTZD"

        JSON example:
        "DateTimeOffsetValue": "2012-12-03T07:16:23Z",

        https://www.w3.org/TR/NOTE-datetime
       """

    def to_literal(self, value: datetime.datetime):
        """Convert python datetime representation to literal format"""

        if not isinstance(value, datetime.datetime):
            raise PyODataModelError(
                'Cannot convert value of type {} to literal. Datetime format is required.'.format(type(value)))

        if value.tzinfo is None:
            raise PyODataModelError(
                'Datetime pass without explicitly setting timezone.  You need to provide timezone information for valid'
                ' Emd.DateTimeOffset')

        # https://www.w3.org/TR/NOTE-datetime =>
        # "Times are expressed in UTC (Coordinated Universal Time), with a special UTC designator ("Z")."
        # "Z" is preferred by ODATA documentation too in contrast to +00:00

        if value.tzinfo == datetime.timezone.utc:
            return super().to_literal(value.replace(tzinfo=None).isoformat() + 'Z')

        return super().to_literal(value.isoformat())

    def to_json(self, value: datetime.datetime):
        return self.to_literal(value)

    def from_literal(self, value: str):

        value = super().from_literal(value)

        try:
            value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f%z')
        except ValueError:
            try:
                value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
            except ValueError:
                raise PyODataModelError('Cannot decode datetime from value {}.'.format(value))

        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)

        return value

    def from_json(self, value: str):
        return self.from_literal(value)


class GeoTypeTraits(TypTraits):
    """ Edm.Geography XXX
        Represents elements which are complaint with geojson specification
    """

    def __getattribute__(self, item):
        if not GEOJSON_MODULE:
            raise PyODataException('To use geography types you need to install pip package geojson')

        return object.__getattribute__(self, item)

    def from_json(self, value: str) -> 'geojson.GeoJSON':
        return geojson.loads(value)

    def to_json(self, value: 'geojson.GeoJSON') -> str:
        return geojson.dumps(value)


class EnumTypTrait(TypTraits):
    """ EnumType type trait """
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
