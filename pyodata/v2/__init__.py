""" This module represents implementation of ODATA V2 """

import logging


from pyodata.version import ODATAVersion, BuildFunctionDict, PrimitiveTypeList, BuildAnnotationDict
from pyodata.model.elements import StructTypeProperty, StructType, ComplexType, EntityType, EntitySet, ValueHelper, \
    ValueHelperParameter, FunctionImport, Typ
from pyodata.model.build_functions import build_value_helper, build_entity_type, build_complex_type, \
    build_value_helper_parameter, build_entity_set, build_struct_type_property, build_struct_type, build_function_import
from pyodata.model.type_traits import EdmBooleanTypTraits, EdmPrefixedTypTraits, EdmIntTypTraits, \
    EdmLongIntTypTraits, EdmStringTypTraits

from .elements import NavigationTypeProperty, EndRole, Association, AssociationSetEndRole, AssociationSet, \
    ReferentialConstraint, Schema
from .build_functions import build_association_set, build_end_role, build_association, build_schema, \
    build_navigation_type_property, build_referential_constraint, build_association_set_end_role
from .type_traits import EdmDateTimeTypTraits


def modlog():
    """ Logging function for debugging."""
    return logging.getLogger("v2")


class ODataV2(ODATAVersion):
    """ Definition of OData V2 """

    @staticmethod
    def build_functions() -> BuildFunctionDict:
        return {
            StructTypeProperty: build_struct_type_property,
            StructType: build_struct_type,
            NavigationTypeProperty: build_navigation_type_property,
            ComplexType: build_complex_type,
            EntityType: build_entity_type,
            EntitySet: build_entity_set,
            EndRole: build_end_role,
            ReferentialConstraint: build_referential_constraint,
            Association: build_association,
            AssociationSetEndRole: build_association_set_end_role,
            AssociationSet: build_association_set,
            ValueHelperParameter: build_value_helper_parameter,
            FunctionImport: build_function_import,
            Schema: build_schema
        }

    @staticmethod
    def primitive_types() -> PrimitiveTypeList:
        return [
            Typ('Null', 'null'),
            Typ('Edm.Binary', 'binary\'\''),
            Typ('Edm.Boolean', 'false', EdmBooleanTypTraits()),
            Typ('Edm.Byte', '0'),
            Typ('Edm.DateTime', 'datetime\'2000-01-01T00:00\'', EdmDateTimeTypTraits()),
            Typ('Edm.Decimal', '0.0M'),
            Typ('Edm.Double', '0.0d'),
            Typ('Edm.Single', '0.0f'),
            Typ('Edm.Guid', 'guid\'00000000-0000-0000-0000-000000000000\'', EdmPrefixedTypTraits('guid')),
            Typ('Edm.Int16', '0', EdmIntTypTraits()),
            Typ('Edm.Int32', '0', EdmIntTypTraits()),
            Typ('Edm.Int64', '0L', EdmLongIntTypTraits()),
            Typ('Edm.SByte', '0'),
            Typ('Edm.String', '\'\'', EdmStringTypTraits()),
            Typ('Edm.Time', 'time\'PT00H00M\''),
            Typ('Edm.DateTimeOffset', 'datetimeoffset\'0000-00-00T00:00:00\'')
        ]

    @staticmethod
    def annotations() -> BuildAnnotationDict:
        return {
            ValueHelper: build_value_helper
        }
