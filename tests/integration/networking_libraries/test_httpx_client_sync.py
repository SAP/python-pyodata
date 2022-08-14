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
