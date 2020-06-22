""" This module represents implementation of ODATA V4 """


from pyodata.version import ODATAVersion, BuildFunctionDict, PrimitiveTypeList, BuildAnnotationDict
from pyodata.model.elements import Typ, Schema, ComplexType, StructType, StructTypeProperty, EntityType
from pyodata.model.build_functions import build_entity_type, build_complex_type, build_struct_type_property, \
    build_struct_type
from pyodata.model.type_traits import EdmBooleanTypTraits, EdmIntTypTraits

from .elements import NavigationTypeProperty, NavigationPropertyBinding, EntitySet, Unit, EnumType
from .build_functions import build_unit_annotation, build_type_definition, build_schema, \
    build_navigation_type_property, build_navigation_property_binding, build_entity_set_with_v4_builder, build_enum_type
from .type_traits import EdmDateTypTraits, GeoTypeTraits, EdmDoubleQuotesEncapsulatedTypTraits, \
    EdmTimeOfDay, EdmDateTimeOffsetTypTraits, EdmDuration
from .service import Service  # noqa


class ODataV4(ODATAVersion):
    """ Definition of OData V4 """

    @staticmethod
    def build_functions() -> BuildFunctionDict:
        return {
            StructTypeProperty: build_struct_type_property,
            StructType: build_struct_type,
            NavigationTypeProperty: build_navigation_type_property,
            NavigationPropertyBinding: build_navigation_property_binding,
            EnumType: build_enum_type,
            ComplexType: build_complex_type,
            EntityType: build_entity_type,
            EntitySet: build_entity_set_with_v4_builder,
            Typ: build_type_definition,
            Schema: build_schema,
        }

    @staticmethod
    def primitive_types() -> PrimitiveTypeList:
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
    def annotations() -> BuildAnnotationDict:
        return {
            Unit: build_unit_annotation
        }
