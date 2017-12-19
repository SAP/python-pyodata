import responses
import requests
import pytest
import pyodata.v2.model
import pyodata.v2.service


@pytest.fixture
def service(metadata):
    """Service fixture"""
    schema = pyodata.v2.model.schema_from_xml(metadata)
    assert len(schema.namespaces) > 0
    return pyodata.v2.service.Service(
        'http://odatapy.example.com/{0}'.format(schema.namespaces[0]),
        schema,
        requests)


@responses.activate
def test_get_entity_property(service):
    """Basic test on getting single property of selected entity"""

    responses.add(
        responses.GET,
        "{0}/MasterEntities(Key='12345')/Key".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    assert service.entity_sets.MasterEntities.get_entity('12345').Key == '12345'


def test_get_entity_property_multiple_key(service):
    """Check identification of entity with key consisting of multiple properites"""
    with pytest.raises(RuntimeError, match=r'Key has.*'):
        service.entity_sets.TemperatureMeasurements.get_entity('12345')
