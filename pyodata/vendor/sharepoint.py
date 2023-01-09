from pyodata.v2.model import (
    TypTraits,
    Typ
)
from pyodata.exceptions import (
    PyODataModelError,
    PyODataException
)
import datetime


class SPEdmDateTimeTypTraits(TypTraits):
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
        super(SPEdmDateTimeTypTraits, self).__init__()

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
        return value.isoformat()

    def to_json(self, value):
        return self.from_literal(value)

    def from_json(self, value):
        return self.from_literal(value)

    def from_literal(self, value):

        if value is None:
            return None

        # Note: parse_datetime_literal raises a PyODataModelError exception on invalid formats
        return datetime.datetime.fromisoformat(value).replace(tzinfo=datetime.timezone.utc)
