""" Test the pyodata integration with httpx client

- it provided sync, requests like interface - FOCUS OF THIS TEST MODULE
- it provides asyncio interface as well

https://www.python-httpx.org/
"""

import httpx
from httpx import Response
import respx
import pytest

import pyodata.v2.service
from pyodata import Client
from pyodata.exceptions import PyODataException, HttpError
from pyodata.v2.model import ParserError, PolicyWarning, PolicyFatal, PolicyIgnore, Config

SERVICE_URL = 'http://example.com'

def test_invalid_odata_version():
    """Check handling of request for invalid OData version implementation"""

    with pytest.raises(PyODataException) as e_info:
        pyodata.Client(SERVICE_URL, httpx, 'INVALID VERSION')

    assert str(e_info.value).startswith('No implementation for selected odata version')


def test_create_client_for_local_metadata(metadata):
    """Check client creation for valid use case with local metadata"""

    client = pyodata.Client(SERVICE_URL, httpx, metadata=metadata)

    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.is_valid == True
    assert len(client.schema.entity_sets) != 0


@pytest.mark.parametrize("content_type", ['application/xml', 'application/atom+xml', 'text/xml'])
def test_create_service_application(respx_mock, metadata, content_type):
    """Check client creation for valid MIME types"""

    # Note: respx_mock is provided by respx package as pytest helper
    headers = httpx.Headers(
        {'Content-Type': content_type}
    )

    respx_mock.get(f"{SERVICE_URL}/$metadata").mock(
        return_value=Response(status_code=200,
                              content=metadata,
                              headers=headers,
                            )
    )

    client = pyodata.Client(SERVICE_URL, httpx)
    assert isinstance(client, pyodata.v2.service.Service)

    # one more test for '/' terminated url
    client = pyodata.Client(SERVICE_URL + '/', httpx)
    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.is_valid


def test_metadata_not_reachable(respx_mock):
    """Check handling of not reachable service metadata"""

    headers = httpx.Headers(
        {'Content-Type': 'text/html'}
    )

    respx_mock.get(f"{SERVICE_URL}/$metadata").mock(
        return_value=Response(status_code=404,
                              headers=headers,
                            )
    )

    with pytest.raises(HttpError) as e_info:
        pyodata.Client(SERVICE_URL, httpx)

    assert str(e_info.value).startswith('Metadata request failed')


def test_metadata_saml_not_authorized(respx_mock):
    """Check handling of not SAML / OAuth unauthorized response"""

    headers = httpx.Headers(
        {'Content-Type': 'text/html; charset=utf-8'}
    )

    respx_mock.get(f"{SERVICE_URL}/$metadata").mock(
        return_value=Response(status_code=200,
                              headers=headers,
                            )
    )

    with pytest.raises(HttpError) as e_info:
        pyodata.Client(SERVICE_URL, httpx)

    assert str(e_info.value).startswith('Metadata request did not return XML, MIME type:')


def test_client_custom_configuration(respx_mock,metadata):
    """Check client creation for custom configuration"""

    headers = httpx.Headers(
        {'Content-Type': 'application/xml'}
    )

    respx_mock.get(f"{SERVICE_URL}/$metadata").mock(
        return_value=Response(status_code=200,
                              headers=headers,
                              content=metadata,
                            )
    )

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
        client = pyodata.Client(SERVICE_URL, httpx, config=custom_config, namespaces=namespaces)

    assert str(e_info.value) == 'You cannot pass namespaces and config at the same time'

    with pytest.warns(DeprecationWarning,match='Passing namespaces directly is deprecated. Use class Config instead'):
        client = pyodata.Client(SERVICE_URL, httpx, namespaces=namespaces)

    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.config.namespaces == namespaces

    client = pyodata.Client(SERVICE_URL, httpx, config=custom_config)

    assert isinstance(client, pyodata.v2.service.Service)
    assert client.schema.config == custom_config