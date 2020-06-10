""" Contains definition of configuration class for PyOData"""

from typing import Type, Dict
from pyodata.policies import PolicyFatal, ParserError, ErrorPolicyType
import pyodata.version


CustomErrorPolicies = Dict[ParserError, ErrorPolicyType]
ODataVersion = Type[pyodata.version.ODATAVersion]
Namespaces = Dict[str, str]
Aliases = Dict[str, str]


class Config:
    # pylint: disable=too-many-instance-attributes,missing-docstring
    # All attributes have purpose and are used for configuration
    # Having docstring for properties is not necessary as we do have type hints

    """ This is configuration class for PyOData. All session dependent settings should be stored here. """

    def __init__(self,
                 odata_version: ODataVersion,
                 custom_error_policies: CustomErrorPolicies = None,
                 default_error_policy: ErrorPolicyType = None,
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
        self._annotation_namespaces = None
        self._aliases: Aliases = dict()

    def err_policy(self, error: ParserError) -> ErrorPolicyType:
        """ Returns error policy for given error. If custom error policy fo error is set, then returns that."""
        if self._custom_error_policy is None:
            return self._default_error_policy

        return self._custom_error_policy.get(error, self._default_error_policy)

    def set_default_error_policy(self, policy: ErrorPolicyType):
        """ Sets default error policy as well as resets custom error policies"""
        self._custom_error_policy = None
        self._default_error_policy = policy

    def set_custom_error_policy(self, policies: Dict[ParserError, ErrorPolicyType]):
        """ Sets custom error policy. It should be called only after setting default error policy, otherwise
            it has no effect. See implementation of "set_default_error_policy" for more details.
        """
        self._custom_error_policy = policies

    @property
    def namespaces(self) -> Namespaces:
        return self._namespaces

    @namespaces.setter
    def namespaces(self, value: Namespaces):
        self._namespaces = value

    @property
    def odata_version(self) -> ODataVersion:
        return self._odata_version

    @property
    def sap_value_helper_directions(self) -> None:
        return self._sap_value_helper_directions

    @property
    def aliases(self) -> Aliases:
        return self._aliases

    @aliases.setter
    def aliases(self, value: Aliases):
        self._aliases = value

    @property
    def annotation_namespace(self) -> None:
        return self._annotation_namespaces
