"""
Interface for request observer, which allows to catch odata request processing details

Author: Michal Nezerka <michal.nezerka@gmail.com>
Date:   2021-05-14
"""

from abc import ABC, abstractmethod


class RequestObserver(ABC):
    """
    The RequestObserver interface declares methods for observing odata request processing.
    """

    @abstractmethod
    def http_response(self, response, request) -> None:
        """
        Get http response together with related http request object.
        """


class RequestObserverLastCall(RequestObserver):
    """
    The implementation of RequestObserver that stored request and response of the last call
    """

    def __init__(self):
        self.response = None
        self.request = None

    def http_response(self, response, request):
        self.response = response
        self.request = request
