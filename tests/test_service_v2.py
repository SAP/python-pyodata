"""Service tests"""

import responses
import requests
import pytest
import pyodata.v2.model
import pyodata.v2.service
from pyodata.exceptions import PyODataException
from pyodata.v2.service import EntityKey

URL_ROOT = 'http://odatapy.example.com'


@pytest.fixture
def service(metadata):
    """Service fixture"""
    schema = pyodata.v2.model.schema_from_xml(metadata)
    assert schema.namespaces   # this is pythonic way how to check > 0

    return pyodata.v2.service.Service(URL_ROOT, schema, requests)


@responses.activate
def test_get_entity_property(service):
    """Basic test on getting single property of selected entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/MasterEntities('12345')".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    assert service.entity_sets.MasterEntities.get_entity('12345').execute().Key == '12345'


@responses.activate
def test_entity_url(service):
    """Test correct build of entity url"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/MasterEntities('12345')".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    entity = service.entity_sets.MasterEntities.get_entity('12345').execute()
    assert entity.url == URL_ROOT + "/MasterEntities('12345')"


def test_get_entity_property_complex_key(service):
    """Check identification of entity with key consisting of multiple properites"""

    # pylint: disable=redefined-outer-name

    with pytest.raises(PyODataException) as e_info:
        service.entity_sets.TemperatureMeasurements.get_entity('12345')

    assert str(e_info.value).startswith('Key of entity type')


def test_entity_key_simple_valid(service):
    """Test valid single value for simple key"""

    # pylint: disable=redefined-outer-name

    key = EntityKey(
        service.schema.entity_type('MasterEntity'),
        '1')

    assert key.to_key_string() == "('1')"


def test_entity_key_simple_named_valid(service):
    """Test valid single named value for simple key"""

    key = EntityKey(
        service.schema.entity_type('MasterEntity'),
        Key='1')

    assert key.to_key_string() == "(Key='1')"


def test_entity_key_simple_named_invalid(service):
    """Test invalid single named value for simple key"""

    with pytest.raises(PyODataException) as e_info:
        EntityKey(
            service.schema.entity_type('MasterEntity'),
            XXX='1')

    assert str(e_info.value).startswith('Missing value for key property Key')


def test_entity_key_complex_valid(service):
    """Test valid creationg of complex key"""

    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1', Date='2017-12-24T18:00')

    assert key.to_key_string() == "(Sensor='sensor1',Date=2017-12-24T18:00)"


def test_entity_key_complex_single_value(service):
    """Test rejection of single value for complex key"""

    with pytest.raises(PyODataException) as e_info:
        EntityKey(
            service.schema.entity_type('TemperatureMeasurement'),
            1)

    assert str(e_info.value).startswith('Key of entity type')
