""" Contains definition of configuration class for PyOData and for ODATA versions. """

from abc import ABC, abstractmethod
from typing import Type, List, Dict, Callable

from pyodata.policies import PolicyFatal, ParserError, ErrorPolicy


class ODATAVersion(ABC):
    """ This is base class for different OData releases. In it we define what are supported types, elements and so on.
        Furthermore, we specify how individual elements are parsed or represented by python objects.
    """

    def __init__(self):
        raise RuntimeError('ODATAVersion and its children are intentionally stateless, '
                           'therefore you can not create instance of them')

    @staticmethod
    @abstractmethod
    def supported_primitive_types() -> List[str]:
        """ Here we define which primitive types are supported and what is their python representation"""

    @staticmethod
    @abstractmethod
    def from_etree_callbacks() -> Dict[object, Callable]:
        """ Here we define which elements are supported and what is their python representation"""

    @classmethod
    def is_primitive_type_supported(cls, type_name):
        """ Convenience method which decides whatever given type is supported."""
        return type_name in cls.supported_primitive_types()


class Config:
    # pylint: disable=too-many-instance-attributes,missing-docstring
    # All attributes have purpose and are used for configuration
    # Having docstring for properties is not necessary as we do have type hints

    """ This is configuration class for PyOData. All session dependent settings should be stored here. """

    def __init__(self,
                 odata_version: Type[ODATAVersion],
                 custom_error_policies=None,
                 default_error_policy=None,
                 xml_namespaces=None
                 ):

        """
        :param custom_error_policies: {ParserError: ErrorPolicy} (default None)
                                      Used to specified individual policies for XML tags. See documentation for more
                                      details.

        :param default_error_policy: ErrorPolicy (default PolicyFatal)
                                     If custom policy is not specified for the tag, the default policy will be used.

        :param xml_namespaces: {str: str} (default None)
        """

        self._custom_error_policy = custom_error_policies

        if default_error_policy is None:
            default_error_policy = PolicyFatal()

        self._default_error_policy = default_error_policy

        if xml_namespaces is None:
            xml_namespaces = {}

        self._namespaces = xml_namespaces

        self._odata_version = odata_version

        self._sap_value_helper_directions = None
        self._sap_annotation_value_list = None
        self._annotation_namespaces = None

    def err_policy(self, error: ParserError) -> ErrorPolicy:
        """ Returns error policy for given error. If custom error policy fo error is set, then returns that."""
        if self._custom_error_policy is None:
            return self._default_error_policy

        return self._custom_error_policy.get(error, self._default_error_policy)

    def set_default_error_policy(self, policy: ErrorPolicy):
        """ Sets default error policy as well as resets custom error policies"""
        self._custom_error_policy = None
        self._default_error_policy = policy

    def set_custom_error_policy(self, policies: Dict[ParserError, Type[ErrorPolicy]]):
        """ Sets custom error policy. It should be called only after setting default error policy, otherwise
            it has no effect. See implementation of "set_default_error_policy" for more details.
        """
        self._custom_error_policy = policies

    @property
    def namespaces(self) -> str:
        return self._namespaces

    @namespaces.setter
    def namespaces(self, value: Dict[str, str]):
        self._namespaces = value

    @property
    def odata_version(self) -> Type[ODATAVersion]:
        return self._odata_version

    @property
    def sap_value_helper_directions(self):
        return self._sap_value_helper_directions

    @property
    def sap_annotation_value_list(self):
        return self._sap_annotation_value_list

    @property
    def annotation_namespace(self):
        return self._annotation_namespaces
