import requests
import pytest
from pytest_localserver.http import WSGIServer

import pyodata.v2.model
import pyodata.v2.service


def odata_service_stub(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'application/json')]
    start_response(status, response_headers)
    return ['{"d": {"Key": "\'12345\'"}}\n']


@pytest.fixture
def http_server(request):
    """Defines the testserver funcarg"""
    server = WSGIServer(application=odata_service_stub)
    server.start()
    request.addfinalizer(server.stop)
    return server


@pytest.fixture
def service(http_server, metadata):
    schema = pyodata.v2.model.schema_from_xml(metadata)
    return pyodata.v2.service.Service('{0}/{1}'.format(http_server.url, schema.namespace), schema, requests)


def test_get_entity_property(service):
    assert service.entity_sets.MasterEntities.get_entity('12345').Key == '12345'


def test_get_entity_property_multiple_key(service):
    """Check identification of entity with key consisting of multiple properites"""
    with pytest.raises(RuntimeError, match=r'Key has.*'):
        service.entity_sets.TemperatureMeasurements.get_entity('12345')
