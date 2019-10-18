""" Repository of elements specific to the ODATA V4"""
from typing import Optional, List

from pyodata.exceptions import PyODataModelError
from pyodata.model.elements import VariableDeclaration, StructType


class NullProperty:
    """ Defines fallback class when parser is unable to process property defined in xml """
    def __init__(self, name):
        self.name = name

    def __getattr__(self, item):
        raise PyODataModelError(f'Cannot access this property. An error occurred during parsing property stated in '
                                f'xml({self.name}) and it was not found, therefore it has been replaced with '
                                f'NullProperty.')


# pylint: disable=missing-docstring
# Purpose of properties is obvious and also they have type hints.
class ReferentialConstraint:
    """ Defines a edm.ReferentialConstraint
        http://docs.oasis-open.org/odata/odata/v4.0/errata03/os/complete/part3-csdl/odata-v4.0-errata03-os-part3-csdl-complete.html#_Toc453752543
    """
    def __init__(self, proprty_name: str, referenced_proprty_name: str):
        self._proprty_name = proprty_name
        self._referenced_proprty_name = referenced_proprty_name
        self._property: Optional[VariableDeclaration] = None
        self._referenced_property: Optional[VariableDeclaration] = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.proprty}, {self.referenced_proprty})"

    def __str__(self):
        return f"{self.__class__.__name__}({self.proprty}, {self.referenced_proprty})"

    @property
    def proprty_name(self):
        return self._proprty_name

    @property
    def referenced_proprty_name(self):
        return self._referenced_proprty_name

    @property
    def proprty(self) -> Optional[VariableDeclaration]:
        return self._property

    @proprty.setter
    def proprty(self, value: VariableDeclaration):
        self._property = value

    @property
    def referenced_proprty(self) -> Optional[VariableDeclaration]:
        return self._referenced_property

    @referenced_proprty.setter
    def referenced_proprty(self, value: VariableDeclaration):
        self._referenced_property = value


class NavigationTypeProperty(VariableDeclaration):
    """Defines a navigation property, which provides a reference to the other end of an association
    """

    def __init__(self, name, type_info, nullable, partner_info, contains_target, referential_constraints):
        super().__init__(name, type_info, nullable, None, None, None)

        self._partner_info = partner_info
        self._partner = None
        self._contains_target = contains_target
        self._referential_constraints = referential_constraints

    @property
    def partner_info(self):
        return self._partner_info

    @property
    def contains_target(self):
        return self._contains_target

    @property
    def partner(self):
        return self._partner

    @partner.setter
    def partner(self, value: StructType):
        self._partner = value

    @property
    def referential_constraints(self) -> List[ReferentialConstraint]:
        return self._referential_constraints
