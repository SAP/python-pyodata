"""PyOData exceptions hierarchy"""


class PyODataException(Exception):
    """Base class for all PyOData exceptions

       Raised when an error is detected that does not fall in any of the other categories.
    """


class PyODataModelError(PyODataException):
    """Raised when model error occurs"""


class PyODataRuntimeError(PyODataException):
    """ Raised when an error accures after initial state is set.
        e. g. when trying to set entity type for EntitySet for the second time
    """


class PyODataValueError(PyODataException):
    """ Raised when an value is invalid
        e. g. malformated input, value is out of range, entity has two properties with same name etc
    """


class PyODataKeyError(PyODataException):
    """ Raised when nonexistent element is requested
        e. g. property, entity set etc...
    """


class PyODataTypeError(PyODataException):
    """ Raised when type error occurs"""


class PyODataParserError(PyODataException):
    """Raised when parser error occurs"""


class ExpressionError(PyODataException):
    """Raise when runtime logical expression error occurs"""


class HttpError(PyODataException):
    """Raised when unexpected HTTP status code is received """

    VendorType = None

    def __new__(cls, message, response):
        if HttpError.VendorType is not None:
            return super(HttpError, cls).__new__(HttpError.VendorType, message, response)

        return super(HttpError, cls).__new__(cls, message, response)

    def __init__(self, message, response):
        super(HttpError, self).__init__(message)

        self.response = response
