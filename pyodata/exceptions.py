"""PyOData exceptions hierarchy"""


class PyODataException(Exception):
    """Base class for all PyOData exceptions

       Raised when an error is detected that does not fall in any of the other categories.
    """


class HttpError(PyODataException):
    """Raised when unexpected HTTP status code is received """

    def __init__(self, message, response):
        super(HttpError, self).__init__(message)

        self.response = response
