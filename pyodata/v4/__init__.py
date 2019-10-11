""" This module represents implementation of ODATA V4 """

from typing import List

from pyodata.model.from_etree_callbacks import enum_type_from_etree, struct_type_property_from_etree, \
    struct_type_from_etree, complex_type_from_etree
from pyodata.config import ODATAVersion
from pyodata.model.type_traits import EdmBooleanTypTraits, EdmIntTypTraits
from pyodata.model.elements import Typ, Schema, EnumType, ComplexType, StructType, StructTypeProperty
from pyodata.v4.type_traits import EdmDateTypTraits, GeoTypeTraits, EdmDoubleQuotesEncapsulatedTypTraits, \
    EdmTimeOfDay, EdmDateTimeOffsetTypTraits, EdmDuration

from pyodata.v4.from_etree_callbacks import schema_from_etree


class ODataV4(ODATAVersion):
    """ Definition of OData V4 """

    @staticmethod
    def from_etree_callbacks():
        return {
            StructTypeProperty: struct_type_property_from_etree,
            StructType: struct_type_from_etree,
            # NavigationTypeProperty: navigation_type_property_from_etree,
            EnumType: enum_type_from_etree,
            ComplexType: complex_type_from_etree,
            Schema: schema_from_etree,
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
