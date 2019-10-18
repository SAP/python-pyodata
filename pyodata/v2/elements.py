""" Repository of elements specific to the ODATA V2"""
# pylint: disable=missing-docstring

import itertools

from pyodata import model
from pyodata.exceptions import PyODataModelError
from pyodata.model.elements import VariableDeclaration


class NullAssociation:
    def __init__(self, name):
        self.name = name

    def __getattr__(self, item):
        raise PyODataModelError('Cannot access this association. An error occurred during parsing '
                                'association metadata due to that annotation has been omitted.')


class NavigationTypeProperty(VariableDeclaration):
    """Defines a navigation property, which provides a reference to the other end of an association

       Unlike properties defined with the Property element, navigation properties do not define the
       shape and characteristics of data. They provide a way to navigate an association between two
       entity types.

       Note that navigation properties are optional on both entity types at the ends of an association.
       If you define a navigation property on one entity type at the end of an association, you do not
       have to define a navigation property on the entity type at the other end of the association.

       The data type returned by a navigation property is determined by the multiplicity of its remote
       association end. For example, suppose a navigation property, OrdersNavProp, exists on a Customer
       entity type and navigates a one-to-many association between Customer and Order. Because the
       remote association end for the navigation property has multiplicity many (*), its data type is
       a collection (of Order). Similarly, if a navigation property, CustomerNavProp, exists on the Order
       entity type, its data type would be Customer since the multiplicity of the remote end is one (1).
    """

    def __init__(self, name, from_role_name, to_role_name, association_info):
        super(NavigationTypeProperty, self).__init__(name, None, False, None, None, None)

        self.from_role_name = from_role_name
        self.to_role_name = to_role_name

        self._association_info = association_info
        self._association = None

    @property
    def association_info(self):
        return self._association_info

    @property
    def association(self):
        return self._association

    @association.setter
    def association(self, value):

        if self._association is not None:
            raise PyODataModelError('Cannot replace {0} of {1} to {2}'.format(self._association, self, value))

        if value.name != self._association_info.name:
            raise PyODataModelError('{0} cannot be the type of {1}'.format(value, self))

        self._association = value

    @property
    def to_role(self):
        return self._association.end_by_role(self.to_role_name)

    @property  # type: ignore
    def typ(self):
        return self.to_role.entity_type


class EndRole:
    MULTIPLICITY_ONE = '1'
    MULTIPLICITY_ZERO_OR_ONE = '0..1'
    MULTIPLICITY_ZERO_OR_MORE = '*'

    def __init__(self, entity_type_info, multiplicity, role):
        self._entity_type_info = entity_type_info
        self._entity_type = None
        self._multiplicity = multiplicity
        self._role = role

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, self.role)

    @property
    def entity_type_info(self):
        return self._entity_type_info

    @property
    def entity_type_name(self):
        return self._entity_type_info.name

    @property
    def entity_type(self):
        return self._entity_type

    @entity_type.setter
    def entity_type(self, value):

        if self._entity_type is not None:
            raise PyODataModelError('Cannot replace {0} of {1} to {2}'.format(self._entity_type, self, value))

        if value.name != self._entity_type_info.name:
            raise PyODataModelError('{0} cannot be the type of {1}'.format(value, self))

        self._entity_type = value

    @property
    def multiplicity(self):
        return self._multiplicity

    @property
    def role(self):
        return self._role


class Association:
    """Defines a relationship between two entity types.

       An association must specify the entity types that are involved in
       the relationship and the possible number of entity types at each
       end of the relationship, which is known as the multiplicity.
       The multiplicity of an association end can have a value of one (1),
       zero or one (0..1), or many (*). This information is specified in
       two child End elements.
    """

    def __init__(self, name):
        self._name = name
        self._referential_constraint = None
        self._end_roles = list()

    def __str__(self):
        return '{0}({1})'.format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name

    @property
    def end_roles(self):
        return self._end_roles

    def end_by_role(self, end_role):
        try:
            return next((item for item in self._end_roles if item.role == end_role))
        except StopIteration:
            raise KeyError('Association {} has no End with Role {}'.format(self._name, end_role))

    @property
    def referential_constraint(self):
        return self._referential_constraint


class AssociationSetEndRole:
    def __init__(self, role, entity_set_name):
        self._role = role
        self._entity_set_name = entity_set_name
        self._entity_set = None

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, self.role)

    @property
    def role(self):
        return self._role

    @property
    def entity_set_name(self):
        return self._entity_set_name

    @property
    def entity_set(self):
        return self._entity_set

    @entity_set.setter
    def entity_set(self, value):
        if self._entity_set:
            raise PyODataModelError('Cannot replace {0} of {1} to {2}'.format(self._entity_set, self, value))

        if value.name != self._entity_set_name:
            raise PyODataModelError(
                'Assigned entity set {0} differentiates from the declared {1}'.format(value, self._entity_set_name))

        self._entity_set = value


class AssociationSet:
    def __init__(self, name, association_type_name, association_type_namespace, end_roles):
        self._name = name
        self._association_type_name = association_type_name
        self._association_type_namespace = association_type_namespace
        self._association_type = None
        self._end_roles = end_roles

    def __str__(self):
        return "{0}({1})".format(self.__class__.__name__, self._name)

    @property
    def name(self):
        return self._name

    @property
    def association_type(self):
        return self._association_type

    @association_type.setter
    def association_type(self, value):
        if self._association_type is not None:
            raise RuntimeError('Cannot replace {} of {} with {}'.format(self._association_type, self, value))
        self._association_type = value

    @property
    def association_type_name(self):
        return self._association_type_name

    @property
    def association_type_namespace(self):
        return self._association_type_namespace

    @property
    def end_roles(self):
        return self._end_roles

    def end_by_role(self, end_role):
        try:
            return next((end for end in self._end_roles if end.role == end_role))
        except StopIteration:
            raise KeyError('Association set {} has no End with Role {}'.format(self._name, end_role))

    def end_by_entity_set(self, entity_set):
        try:
            return next((end for end in self._end_roles if end.entity_set_name == entity_set))
        except StopIteration:
            raise KeyError('Association set {} has no End with Entity Set {}'.format(self._name, entity_set))


class ReferentialConstraintRole:
    def __init__(self, name, property_names):
        self._name = name
        self._property_names = property_names

    @property
    def name(self):
        return self._name

    @property
    def property_names(self):
        return self._property_names


class PrincipalRole(ReferentialConstraintRole):
    pass


class DependentRole(ReferentialConstraintRole):
    pass


class ReferentialConstraint:
    def __init__(self, principal, dependent):
        self._principal = principal
        self._dependent = dependent

    @property
    def principal(self):
        return self._principal

    @property
    def dependent(self):
        return self._dependent


class Schema(model.elements.Schema):
    def association(self, association_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].associations[association_name]
            except KeyError:
                raise KeyError('Association {} does not exist in namespace {}'.format(association_name, namespace))
        for decl in list(self._decls.values()):
            try:
                return decl.associations[association_name]
            except KeyError:
                pass

    @property
    def associations(self):
        return list(itertools.chain(*(decl.list_associations() for decl in list(self._decls.values()))))

    def association_set_by_association(self, association_name, namespace=None):
        if namespace is not None:
            for association_set in list(self._decls[namespace].association_sets.values()):
                if association_set.association_type.name == association_name:
                    return association_set
            raise KeyError('Association Set for Association {} does not exist in Schema Namespace {}'.format(
                association_name, namespace))
        for decl in list(self._decls.values()):
            for association_set in list(decl.association_sets.values()):
                if association_set.association_type.name == association_name:
                    return association_set
        raise KeyError('Association Set for Association {} does not exist in any Schema Namespace'.format(
            association_name))

    def association_set(self, set_name, namespace=None):
        if namespace is not None:
            try:
                return self._decls[namespace].association_sets[set_name]
            except KeyError:
                raise KeyError('Association set {} does not exist in namespace {}'.format(set_name, namespace))
        for decl in list(self._decls.values()):
            try:
                return decl.association_sets[set_name]
            except KeyError:
                pass

    @property
    def association_sets(self):
        return list(itertools.chain(*(decl.list_association_sets() for decl in list(self._decls.values()))))
