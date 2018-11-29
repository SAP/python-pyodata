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
def test_create_service_application_xml(metadata):
    """Check client creation for valid use case with MIME type 'application/xml'"""

    responses.add(
        responses.GET,
        "{0}/$metadata".format(SERVICE_URL),
        content_type='application/xml',
        body=metadata,
        status=200)

    client = pyodata.Client(SERVICE_URL, requests)

    assert isinstance(client, pyodata.v2.service.Service)

    # onw more test for '/' terminated url

    client = pyodata.Client(SERVICE_URL + '/', requests)

    assert isinstance(client, pyodata.v2.service.Service)


@responses.activate
def test_create_service_text_xml(metadata):
    """Check client creation for valid use case with MIME type 'text/xml'"""

    responses.add(
        responses.GET,
        "{0}/$metadata".format(SERVICE_URL),
        content_type='text/xml',
        body=metadata,
        status=200)

    client = pyodata.Client(SERVICE_URL, requests)

    assert isinstance(client, pyodata.v2.service.Service)

    # onw more test for '/' terminated url

    client = pyodata.Client(SERVICE_URL + '/', requests)

    assert isinstance(client, pyodata.v2.service.Service)


@responses.activate
def test_metadata_not_reachable():
    """Check handling of not reachable service metadata"""

    responses.add(
        responses.GET,
        "{0}/$metadata".format(SERVICE_URL),
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
        "{0}/$metadata".format(SERVICE_URL),
        content_type='text/html; charset=utf-8',
        status=200)

    with pytest.raises(HttpError) as e_info:
        pyodata.Client(SERVICE_URL, requests)

    assert str(e_info.value).startswith('Metadata request did not return XML, MIME type:')
