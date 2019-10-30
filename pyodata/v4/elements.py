""" Repository of elements specific to the ODATA V4"""
from typing import Optional, List

from pyodata.exceptions import PyODataModelError, PyODataException
from pyodata.model.elements import VariableDeclaration, StructType, Identifier
from pyodata.model.type_traits import TypTraits
from pyodata.v4.type_traits import EnumTypTrait


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


class EnumMember:
    """ Represents individual enum values """
    def __init__(self, parent, name, value):
        self._parent = parent
        self._name = name
        self._value = value

    def __str__(self):
        return f"{self._parent.name}\'{self._name}\'"

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def parent(self):
        return self._parent


class EnumType(Identifier):
    """ Represents enum type """
    def __init__(self, name, is_flags, underlying_type, namespace):
        super(EnumType, self).__init__(name)
        self._member = list()
        self._underlying_type = underlying_type
        self._traits = TypTraits()
        self._namespace = namespace

        if is_flags == 'True':
            self._is_flags = True
        else:
            self._is_flags = False

    def __str__(self):
        return f"{self.__class__.__name__}({self._name})"

    def __getattr__(self, item):
        member = next(filter(lambda x: x.name == item, self._member), None)
        if member is None:
            raise PyODataException(f'EnumType {self} has no member {item}')

        return member

    def __getitem__(self, item):
        # If the item is type string then we want to check for members with that name instead
        if isinstance(item, str):
            return self.__getattr__(item)

        member = next(filter(lambda x: x.value == int(item), self._member), None)
        if member is None:
            raise PyODataException(f'EnumType {self} has no member with value {item}')

        return member

    @property
    def is_flags(self):
        return self._is_flags

    @property
    def traits(self):
        return EnumTypTrait(self)

    @property
    def namespace(self):
        return self._namespace
