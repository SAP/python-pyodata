""" Repository of elements specific to the ODATA V4"""
from typing import Optional, List

import collections

from pyodata.model import elements
from pyodata.exceptions import PyODataModelError
from pyodata.model.elements import VariableDeclaration, StructType, TypeInfo, Annotation

PathInfo = collections.namedtuple('PathInfo', 'namespace type proprty')


def to_path_info(value: str, et_info: TypeInfo):
    """ Helper function for parsing Path attribute on NavigationPropertyBinding property """
    if '/' in value:
        parts = value.split('.')
        entity_name, property_name = parts[-1].split('/')
        return PathInfo('.'.join(parts[:-1]), entity_name, property_name)

    return PathInfo(et_info.namespace, et_info.name, value)


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


class NavigationPropertyBinding:
    """ Describes which entity set of navigation property contains related entities
        https://docs.oasis-open.org/odata/odata-csdl-xml/v4.01/csprd06/odata-csdl-xml-v4.01-csprd06.html#sec_NavigationPropertyBinding
    """

    def __init__(self, path_info: PathInfo, target_info: str):
        self._path_info = path_info
        self._target_info = target_info
        self._path: Optional[NavigationTypeProperty] = None
        self._target: Optional['EntitySet'] = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.path}, {self.target})"

    def __str__(self):
        return f"{self.__class__.__name__}({self.path}, {self.target})"

    @property
    def path_info(self) -> PathInfo:
        return self._path_info

    @property
    def target_info(self):
        return self._target_info

    @property
    def path(self) -> Optional[NavigationTypeProperty]:
        return self._path

    @path.setter
    def path(self, value: NavigationTypeProperty):
        self._path = value

    @property
    def target(self) -> Optional['EntitySet']:
        return self._target

    @target.setter
    def target(self, value: 'EntitySet'):
        self._target = value


# pylint: disable=too-many-arguments
class EntitySet(elements.EntitySet):
    """ EntitySet complaint with OData V4
        https://docs.oasis-open.org/odata/odata-csdl-xml/v4.01/csprd06/odata-csdl-xml-v4.01-csprd06.html#sec_EntitySet
    """
    def __init__(self, name, entity_type_info, addressable, creatable, updatable, deletable, searchable, countable,
                 pageable, topable, req_filter, label, navigation_property_bindings):
        super(EntitySet, self).__init__(name, entity_type_info, addressable, creatable, updatable, deletable,
                                        searchable, countable, pageable, topable, req_filter, label)

        self._navigation_property_bindings = navigation_property_bindings

    @property
    def navigation_property_bindings(self) -> List[NavigationPropertyBinding]:
        return self._navigation_property_bindings


class Unit(Annotation):

    def __init__(self, target, unit_name: str):
        super(Unit, self).__init__(target)
        self._unit_name = unit_name

    @staticmethod
    def term() -> str:
        return 'Org.OData.Measures.V1.Unit'

    @property
    def unit_name(self) -> str:
        return self._unit_name
