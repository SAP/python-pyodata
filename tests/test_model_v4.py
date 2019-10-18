import json
import datetime
import geojson
import pytest

from pyodata.model.builder import MetadataBuilder
from pyodata.exceptions import PyODataModelError
from pyodata.model.type_traits import TypTraits
from pyodata.model.elements import Types

from pyodata.config import Config
from pyodata.v4 import ODataV4
from tests.conftest import metadata
from v4 import NavigationTypeProperty


def test_type_traits():
    """Test traits"""
    # https://docs.oasis-open.org/odata/odata-json-format/v4.01/csprd05/odata-json-format-v4.01-csprd05.html#sec_PrimitiveValue

    config = Config(ODataV4)

    traits = Types.from_name('Edm.Date', config).traits
    test_date = datetime.date(2005, 1, 28)
    test_date_json = traits.to_json(test_date)
    assert test_date_json == '\"2005-01-28\"'
    assert test_date == traits.from_json(test_date_json)

    traits = Types.from_name('Edm.TimeOfDay', config).traits
    test_time = datetime.time(7, 59, 59)
    test_time_json = traits.to_json(test_time)
    assert test_time_json == '\"07:59:59\"'
    assert test_time == traits.from_json(test_time_json)

    traits = Types.from_name('Edm.DateTimeOffset', config).traits
    test_date_time_offset = datetime.datetime(2012, 12, 3, 7, 16, 23, tzinfo=datetime.timezone.utc)
    test_date_time_offset_json = traits.to_json(test_date_time_offset)
    assert test_date_time_offset_json == '\"2012-12-03T07:16:23Z\"'
    assert test_date_time_offset == traits.from_json(test_date_time_offset_json)
    assert test_date_time_offset == traits.from_json('\"2012-12-03T07:16:23+00:00\"')

    # serialization of invalid value
    with pytest.raises(PyODataModelError) as e_info:
        traits.to_literal('xyz')
    assert str(e_info.value).startswith('Cannot convert value of type')

    traits = Types.from_name('Edm.Duration', config).traits

    test_duration_json = 'P8MT4H'
    test_duration = traits.from_json(test_duration_json)
    assert test_duration.month == 8
    assert test_duration.hour == 4
    assert test_duration_json == traits.to_json(test_duration)

    test_duration_json = 'P2Y6M5DT12H35M30S'
    test_duration = traits.from_json(test_duration_json)
    assert test_duration.year == 2
    assert test_duration.month == 6
    assert test_duration.day == 5
    assert test_duration.hour == 12
    assert test_duration.minute == 35
    assert test_duration.second == 30
    assert test_duration_json == traits.to_json(test_duration)

    # GeoJson Point

    json_point = json.dumps({
        "type": "Point",
        "coordinates": [-118.4080, 33.9425]
    })

    traits = Types.from_name('Edm.GeographyPoint', config).traits
    point = traits.from_json(json_point)

    assert isinstance(point, geojson.Point)
    assert json_point == traits.to_json(point)

    # GeoJson MultiPoint

    json_multi_point = json.dumps({
        "type": "MultiPoint",
        "coordinates": [[100.0, 0.0], [101.0, 1.0]]
    })

    traits = Types.from_name('Edm.GeographyMultiPoint', config).traits
    multi_point = traits.from_json(json_multi_point)

    assert isinstance(multi_point, geojson.MultiPoint)
    assert json_multi_point == traits.to_json(multi_point)

    # GeoJson LineString

    json_line_string = json.dumps({
        "type": "LineString",
        "coordinates": [[102.0, 0.0], [103.0, 1.0], [104.0, 0.0], [105.0, 1.0]]
    })

    traits = Types.from_name('Edm.GeographyLineString', config).traits
    line_string = traits.from_json(json_line_string)

    assert isinstance(line_string, geojson.LineString)
    assert json_line_string == traits.to_json(line_string)

    # GeoJson MultiLineString

    lines = []
    for i in range(10):
        lines.append(geojson.utils.generate_random("LineString")['coordinates'])

    multi_line_string = geojson.MultiLineString(lines)
    json_multi_line_string = geojson.dumps(multi_line_string)
    traits = Types.from_name('Edm.GeographyMultiLineString', config).traits

    assert multi_line_string == traits.from_json(json_multi_line_string)
    assert json_multi_line_string == traits.to_json(multi_line_string)

    # GeoJson Polygon

    json_polygon = json.dumps({
        "type": "Polygon",
        "coordinates": [
            [[100.0, 0.0], [105.0, 0.0], [100.0, 1.0]],
            [[100.2, 0.2], [103.0, 0.2], [100.3, 0.8]]
        ]
    })

    traits = Types.from_name('Edm.GeographyPolygon', config).traits
    polygon = traits.from_json(json_polygon)

    assert isinstance(polygon, geojson.Polygon)
    assert json_polygon == traits.to_json(polygon)

    # GeoJson MultiPolygon

    lines = []
    for i in range(10):
        lines.append(geojson.utils.generate_random("Polygon")['coordinates'])

    multi_polygon = geojson.MultiLineString(lines)
    json_multi_polygon = geojson.dumps(multi_polygon)
    traits = Types.from_name('Edm.GeographyMultiPolygon', config).traits

    assert multi_polygon == traits.from_json(json_multi_polygon)
    assert json_multi_polygon == traits.to_json(multi_polygon)


def test_schema(metadata_v4):
    meta_builder = MetadataBuilder(
        metadata_v4,
        config=Config(ODataV4)
    )

    meta_builder.build()


def test_edmx_navigation_properties(schema_v4):
    """Test parsing of navigation properties"""

    entity = schema_v4.entity_type('Person')
    assert str(entity) == 'EntityType(Person)'
    assert entity.name == 'Person'

    nav_prop = entity.nav_proprty('Friends')
    assert str(nav_prop) == 'NavigationTypeProperty(Friends)'
    assert repr(nav_prop.typ) == 'Collection(EntityType(Person))'
    assert repr(nav_prop.partner) == 'NavigationTypeProperty(Friends)'


def test_referential_constraint(schema_v4):
    nav_property: NavigationTypeProperty = schema_v4.entity_type('Product').nav_proprty('Category')
    assert str(nav_property) == 'NavigationTypeProperty(Category)'
    assert repr(nav_property.referential_constraints[0]) == \
        'ReferentialConstraint(StructTypeProperty(CategoryID), StructTypeProperty(ID))'

