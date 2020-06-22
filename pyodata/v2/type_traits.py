""" Type traits for types specific to the ODATA V4"""

import datetime
import re

from pyodata.exceptions import PyODataModelError
from pyodata.model.type_traits import EdmPrefixedTypTraits


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
