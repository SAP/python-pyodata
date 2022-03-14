"""PyOData Client tests"""
from unittest.mock import patch

import aiohttp
import pytest
from aiohttp import web

import pyodata.v2.service
from pyodata import Client
from pyodata.exceptions import PyODataException, HttpError
from pyodata.v2.model import ParserError, PolicyWarning, PolicyFatal, PolicyIgnore, Config

SERVICE_URL = ''


async def test_invalid_odata_version():
    """Check handling of request for invalid OData version implementation"""

    with pytest.raises(PyODataException) as e_info:
        async with aiohttp.ClientSession() as client:
            await Client.build_async_client(SERVICE_URL, client, 'INVALID VERSION')

    assert str(e_info.value).startswith('No implementation for selected odata version')


async def test_create_client_for_local_metadata(metadata):
    """Check client creation for valid use case with local metadata"""

    async with aiohttp.ClientSession() as client:
        service_client = await Client.build_async_client(SERVICE_URL, client, metadata=metadata)

        assert isinstance(service_client, pyodata.v2.service.Service)
        assert service_client.schema.is_valid == True

        assert len(service_client.schema.entity_sets) != 0


def generate_metadata_response(headers=None, body=None, status=200):
    async def metadata_repsonse(request):
        return web.Response(status=status, headers=headers, body=body)

    return metadata_repsonse


@pytest.mark.parametrize("content_type", ['application/xml', 'application/atom+xml', 'text/xml'])
async def test_create_service_application(aiohttp_client, metadata, content_type):
    """Check client creation for valid MIME types"""

    app = web.Application()
    app.router.add_get('/$metadata', generate_metadata_response(headers={'content-type': content_type}, body=metadata))
    client = await aiohttp_client(app)

    service_client = await Client.build_async_client(SERVICE_URL, client)

    assert isinstance(service_client, pyodata.v2.service.Service)

    # one more test for '/' terminated url

    service_client = await Client.build_async_client(SERVICE_URL + '/', client)

    assert isinstance(service_client, pyodata.v2.service.Service)
    assert service_client.schema.is_valid


async def test_metadata_not_reachable(aiohttp_client):
    """Check handling of not reachable service metadata"""

    app = web.Application()
    app.router.add_get('/$metadata', generate_metadata_response(headers={'content-type': 'text/html'}, status=404))
    client = await aiohttp_client(app)

    with pytest.raises(HttpError) as e_info:
        await Client.build_async_client(SERVICE_URL, client)

    assert str(e_info.value).startswith('Metadata request failed')


async def test_metadata_saml_not_authorized(aiohttp_client):
    """Check handling of not SAML / OAuth unauthorized response"""

    app = web.Application()
    app.router.add_get('/$metadata', generate_metadata_response(headers={'content-type': 'text/html; charset=utf-8'}))
    client = await aiohttp_client(app)

    with pytest.raises(HttpError) as e_info:
        await Client.build_async_client(SERVICE_URL, client)

    assert str(e_info.value).startswith('Metadata request did not return XML, MIME type:')


@patch('warnings.warn')
async def test_client_custom_configuration(mock_warning, aiohttp_client, metadata):
    """Check client creation for custom configuration"""

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

    app = web.Application()
    app.router.add_get('/$metadata',
                       generate_metadata_response(headers={'content-type': 'application/xml'}, body=metadata))
    client = await aiohttp_client(app)

    with pytest.raises(PyODataException) as e_info:
        await Client.build_async_client(SERVICE_URL, client, config=custom_config, namespaces=namespaces)

    assert str(e_info.value) == 'You cannot pass namespaces and config at the same time'

    service = await Client.build_async_client(SERVICE_URL, client, namespaces=namespaces)

    mock_warning.assert_called_with(
        'Passing namespaces directly is deprecated. Use class Config instead',
        DeprecationWarning
    )
    assert isinstance(service, pyodata.v2.service.Service)
    assert service.schema.config.namespaces == namespaces

    service = await Client.build_async_client(SERVICE_URL, client, config=custom_config)

    assert isinstance(service, pyodata.v2.service.Service)
    assert service.schema.config == custom_config
