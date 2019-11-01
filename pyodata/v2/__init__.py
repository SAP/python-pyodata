""" This module represents implementation of ODATA V2 """

import logging
from typing import List

from pyodata.v2.type_traits import EdmDateTimeTypTraits

from pyodata.model.type_traits import EdmBooleanTypTraits, EdmPrefixedTypTraits, EdmIntTypTraits, \
    EdmLongIntTypTraits, EdmStringTypTraits
from pyodata.config import ODATAVersion

from pyodata.v2.elements import NavigationTypeProperty, EndRole, Association, AssociationSetEndRole, AssociationSet, \
    ReferentialConstraint, Schema
from pyodata.model.elements import StructTypeProperty, StructType, ComplexType, EntityType, EntitySet, ValueHelper, \
    ValueHelperParameter, FunctionImport, Typ


import pyodata.v2.build_functions as build_functions_v2
import pyodata.model.build_functions as build_functions


def modlog():
    """ Logging function for debugging."""
    return logging.getLogger("v2")


class ODataV2(ODATAVersion):
    """ Definition of OData V2 """

    @staticmethod
    def build_functions():
        return {
            StructTypeProperty: build_functions.build_struct_type_property,
            StructType: build_functions.build_struct_type,
            NavigationTypeProperty: build_functions_v2.build_navigation_type_property,
            ComplexType: build_functions.build_complex_type,
            EntityType: build_functions.build_entity_type,
            EntitySet: build_functions.build_entity_set,
            EndRole: build_functions_v2.build_end_role,
            ReferentialConstraint: build_functions_v2.build_referential_constraint,
            Association: build_functions_v2.build_association,
            AssociationSetEndRole: build_functions_v2.build_association_set_end_role,
            AssociationSet: build_functions_v2.build_association_set,
            ValueHelperParameter: build_functions.build_value_helper_parameter,
            FunctionImport: build_functions.build_function_import,
            Schema: build_functions_v2.build_schema
        }

    @staticmethod
    def primitive_types() -> List[Typ]:
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
    def annotations():
        return {
            ValueHelper: build_functions.build_value_helper
        }
