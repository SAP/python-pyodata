"""PyOData exceptions hierarchy"""


class PyODataException(Exception):
    """Base class for all PyOData exceptions

       Raised when an error is detected that does not fall in any of the other categories.
    """


class PyODataModelError(PyODataException):
    """Raised when model error occurs"""


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


class ProgramError(PyODataException):
    """Raised when an error in the program logic occurs"""
