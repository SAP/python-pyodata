""" This module represents implementation of ODATA V4 """

from typing import List

from pyodata.config import ODATAVersion
from pyodata.model.type_traits import EdmBooleanTypTraits, EdmIntTypTraits
from pyodata.model.elements import Typ, Schema, ComplexType, StructType, StructTypeProperty, EntityType

from pyodata.v4.elements import NavigationTypeProperty, NavigationPropertyBinding, EntitySet, Unit, EnumType
from pyodata.v4.type_traits import EdmDateTypTraits, GeoTypeTraits, EdmDoubleQuotesEncapsulatedTypTraits, \
    EdmTimeOfDay, EdmDateTimeOffsetTypTraits, EdmDuration

import pyodata.v4.build_functions as build_functions_v4
import pyodata.model.build_functions as build_functions


class ODataV4(ODATAVersion):
    """ Definition of OData V4 """

    @staticmethod
    def build_functions():
        return {
            StructTypeProperty: build_functions.build_struct_type_property,
            StructType: build_functions.build_struct_type,
            NavigationTypeProperty: build_functions_v4.build_navigation_type_property,
            NavigationPropertyBinding: build_functions_v4.build_navigation_property_binding,
            EnumType: build_functions_v4.build_enum_type,
            ComplexType: build_functions.build_complex_type,
            EntityType: build_functions.build_entity_type,
            EntitySet: build_functions.build_entity_set,
            Typ: build_functions_v4.build_type_definition,
            Schema: build_functions_v4.build_schema,
        }

    @staticmethod
    def primitive_types() -> List[Typ]:
        # TODO: We currently lack support for:
        #   'Edm.Geometry',
        #   'Edm.GeometryPoint',
        #   'Edm.GeometryLineString',
        #   'Edm.GeometryPolygon',
        #   'Edm.GeometryMultiPoint',
        #   'Edm.GeometryMultiLineString',
        #   'Edm.GeometryMultiPolygon',
        #   'Edm.GeometryCollection',

        return [
            Typ('Null', 'null'),
            Typ('Edm.Binary', '', EdmDoubleQuotesEncapsulatedTypTraits()),
            Typ('Edm.Boolean', 'false', EdmBooleanTypTraits()),
            Typ('Edm.Byte', '0'),
            Typ('Edm.Date', '0000-00-00', EdmDateTypTraits()),
            Typ('Edm.Decimal', '0.0'),
            Typ('Edm.Double', '0.0'),
            Typ('Edm.Duration', 'P', EdmDuration()),
            Typ('Edm.Stream', 'null', EdmDoubleQuotesEncapsulatedTypTraits()),
            Typ('Edm.Single', '0.0', EdmDoubleQuotesEncapsulatedTypTraits()),
            Typ('Edm.Guid', '\"00000000-0000-0000-0000-000000000000\"', EdmDoubleQuotesEncapsulatedTypTraits()),
            Typ('Edm.Int16', '0', EdmIntTypTraits()),
            Typ('Edm.Int32', '0', EdmIntTypTraits()),
            Typ('Edm.Int64', '0', EdmIntTypTraits()),
            Typ('Edm.SByte', '0'),
            Typ('Edm.String', '\"\"', EdmDoubleQuotesEncapsulatedTypTraits()),
            Typ('Edm.TimeOfDay', '00:00:00', EdmTimeOfDay()),
            Typ('Edm.DateTimeOffset', '0000-00-00T00:00:00', EdmDateTimeOffsetTypTraits()),
            Typ('Edm.Geography', '', GeoTypeTraits()),
            Typ('Edm.GeographyPoint', '', GeoTypeTraits()),
            Typ('Edm.GeographyLineString', '', GeoTypeTraits()),
            Typ('Edm.GeographyPolygon', '', GeoTypeTraits()),
            Typ('Edm.GeographyMultiPoint', '', GeoTypeTraits()),
            Typ('Edm.GeographyMultiLineString', '', GeoTypeTraits()),
            Typ('Edm.GeographyMultiPolygon', '', GeoTypeTraits()),
        ]

    @staticmethod
    def annotations():
        return {
            Unit: build_functions_v4.build_unit_annotation
        }
