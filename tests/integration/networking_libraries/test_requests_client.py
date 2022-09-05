""" Test the pyodata integration with Requests library.

https://requests.readthedocs.io/en/latest/
"""

import responses
import requests
import pytest
import pyodata
import pyodata.v2.service
from pyodata.exceptions import PyODataException, HttpError
from pyodata.v2.model import ParserError, PolicyWarning, PolicyFatal, PolicyIgnore, Config

SERVICE_URL = 'http://example.com'



@responses.activate
def test_invalid_odata_version():
    """Check handling of request for invalid OData version implementation"""

    with pytest.raises(PyODataException) as e_info:
        pyodata.Client(SERVICE_URL, requests, 'INVALID VERSION')

    assert str(e_info.value).startswith('No implementation for selected odata version')


@responses.activate
def test_create_client_for_local_metadata(metadata):
    """Check client creation for valid use case with local metadata"""

    client = pyodata.Client(SERVICE_URL, requests, metadata=metadata)

    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.is_valid == True

    assert len(client.schema.entity_sets) != 0


@responses.activate
@pytest.mark.parametrize("content_type", ['application/xml', 'application/atom+xml', 'text/xml'])
def test_create_service_application(metadata, content_type):
    """Check client creation for valid MIME types"""

    responses.add(
        responses.GET,
        f"{SERVICE_URL}/$metadata",
        content_type=content_type,
        body=metadata,
        status=200)

    client = pyodata.Client(SERVICE_URL, requests)

    assert isinstance(client, pyodata.v2.service.Service)

    # one more test for '/' terminated url

    client = pyodata.Client(SERVICE_URL + '/', requests)

    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.is_valid


@responses.activate
def test_metadata_not_reachable():
    """Check handling of not reachable service metadata"""

    responses.add(
        responses.GET,
        f"{SERVICE_URL}/$metadata",
        content_type='text/html',
        status=404)

    with pytest.raises(HttpError) as e_info:
        pyodata.Client(SERVICE_URL, requests)

    assert str(e_info.value).startswith('Metadata request failed')

@responses.activate
def test_metadata_saml_not_authorized():
    """Check handling of not SAML / OAuth unauthorized response"""

    responses.add(
        responses.GET,
        f"{SERVICE_URL}/$metadata",
        content_type='text/html; charset=utf-8',
        status=200)

    with pytest.raises(HttpError) as e_info:
        pyodata.Client(SERVICE_URL, requests)

    assert str(e_info.value).startswith('Metadata request did not return XML, MIME type:')


@responses.activate
def test_client_custom_configuration(metadata):
    """Check client creation for custom configuration"""

    responses.add(
        responses.GET,
        f"{SERVICE_URL}/$metadata",
        content_type='application/xml',
        body=metadata,
        status=200)

    namespaces = {
        'edmx': "customEdmxUrl.com",
        'edm': 'customEdmUrl.com'
    }

    custom_config = Config(
        xml_namespaces=namespaces,
        default_error_policy=PolicyFatal(),
        custom_error_policies={
            ParserError.ANNOTATION: PolicyWarning(),
            ParserError.ASSOCIATION: PolicyIgnore()
        })

    with pytest.raises(PyODataException) as e_info:
        client = pyodata.Client(SERVICE_URL, requests, config=custom_config, namespaces=namespaces)

    assert str(e_info.value) == 'You cannot pass namespaces and config at the same time'

    with pytest.warns(DeprecationWarning,match='Passing namespaces directly is deprecated. Use class Config instead'):
        client = pyodata.Client(SERVICE_URL, requests, namespaces=namespaces)

    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.config.namespaces == namespaces

    client = pyodata.Client(SERVICE_URL, requests, config=custom_config)

    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.config == custom_config
