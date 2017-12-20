"""PyOData Client tests"""

import responses
import requests
import pytest
import pyodata
import pyodata.v2.service
from pyodata.exceptions import PyODataException, HttpError

SERVICE_URL = 'http://example.com'


@responses.activate
def test_invalid_odata_version():
    """Check handling of request for invalid OData version implementation"""

    with pytest.raises(PyODataException) as e_info:
        pyodata.Client(SERVICE_URL, requests, 'INVALID VERSION')

    assert str(e_info.value).startswith('No implementation for selected odata version')


@responses.activate
def test_create_service(metadata):
    """Check client creation for valid use case"""

    responses.add(
        responses.GET,
        "{0}/$metadata".format(SERVICE_URL),
        headers={'Content-type': 'text/xml'},
        body=metadata,
        status=200)

    client = pyodata.Client(SERVICE_URL, requests)

    assert isinstance(client, pyodata.v2.service.Service)

    # onw more test for '/' terminated url

    client = pyodata.Client(SERVICE_URL + '/', requests)

    assert isinstance(client, pyodata.v2.service.Service)
