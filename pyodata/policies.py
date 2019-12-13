"""
    This module servers as repository of different kind of errors which can be encounter during parsing and
    policies which defines how the parser should response to given error.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TypeVar


class ParserError(Enum):
    """ Represents all the different errors the parser is able to deal with."""
    PROPERTY = auto()
    NAVIGATION_PROPERTY = auto()
    NAVIGATION_PROPERTY_BIDING = auto()
    ANNOTATION = auto()
    ASSOCIATION = auto()

    ENUM_TYPE = auto()
    ENTITY_TYPE = auto()
    ENTITY_SET = auto()
    COMPLEX_TYPE = auto()
    REFERENTIAL_CONSTRAINT = auto()


ErrorPolicyType = TypeVar("ErrorPolicyType", bound="ErrorPolicy")


class ErrorPolicy(ABC):
    """ All policies has to inhere this class"""
    @abstractmethod
    def resolve(self, ekseption):
        """ This method is invoked when an error arise."""


class PolicyFatal(ErrorPolicy):
    """ Encounter error should result in parser failing. """
    def resolve(self, ekseption):
        raise ekseption


class PolicyWarning(ErrorPolicy):
    """ Encounter error is logged, but parser continues as nothing has happened """
    def __init__(self):
        logging.basicConfig(format='%(levelname)s: %(message)s')
        self._logger = logging.getLogger()

    def resolve(self, ekseption):
        self._logger.warning('[%s] %s', ekseption.__class__.__name__, str(ekseption))


class PolicyIgnore(ErrorPolicy):
    """ Encounter error is ignored and parser continues as nothing has happened """
    def resolve(self, ekseption):
        pass
