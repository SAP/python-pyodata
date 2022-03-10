"""PyOData Client tests"""
from unittest.mock import patch, AsyncMock

import aiohttp
import pytest
import requests.adapters

import pyodata.v2.service
from pyodata import Client
from pyodata.exceptions import PyODataException, HttpError
from pyodata.v2.model import ParserError, PolicyWarning, PolicyFatal, PolicyIgnore, Config

SERVICE_URL = 'http://example.com'


@pytest.mark.asyncio
async def test_invalid_odata_version():
    """Check handling of request for invalid OData version implementation"""

    with pytest.raises(PyODataException) as e_info:
        async with aiohttp.ClientSession() as client:
            await Client.build_async_client(SERVICE_URL, client, 'INVALID VERSION')

    assert str(e_info.value).startswith('No implementation for selected odata version')


@pytest.mark.asyncio
async def test_create_client_for_local_metadata(metadata):
    """Check client creation for valid use case with local metadata"""

    async with aiohttp.ClientSession() as client:
        service_client = await Client.build_async_client(SERVICE_URL, client, metadata=metadata)

        assert isinstance(service_client, pyodata.v2.service.Service)
        assert service_client.schema.is_valid == True

        assert len(service_client.schema.entity_sets) != 0


@patch("pyodata.client._async_fetch_metadata")
@pytest.mark.parametrize("content_type", ['application/xml', 'application/atom+xml', 'text/xml'])
@pytest.mark.asyncio
async def test_create_service_application(mock_fetch_metadata, metadata, content_type):
    """Check client creation for valid MIME types"""
    mock_fetch_metadata.return_value = metadata

    async with aiohttp.ClientSession() as client:
        service_client = await Client.build_async_client(SERVICE_URL, client)

        assert isinstance(service_client, pyodata.v2.service.Service)

        # one more test for '/' terminated url

        service_client = await Client.build_async_client(SERVICE_URL + '/', requests)

        assert isinstance(service_client, pyodata.v2.service.Service)
        assert service_client.schema.is_valid


@patch("aiohttp.client.ClientSession.get")
@pytest.mark.asyncio
async def test_metadata_not_reachable(mock):
    """Check handling of not reachable service metadata"""

    response = AsyncMock()
    response.status = 404
    response.headers = {'content-type': 'text/html'}
    mock.return_value.__aenter__.return_value = response

    with pytest.raises(HttpError) as e_info:
        async with aiohttp.ClientSession() as client:
            await Client.build_async_client(SERVICE_URL, client)

    assert str(e_info.value).startswith('Metadata request failed')


@patch("aiohttp.client.ClientSession.get")
@pytest.mark.asyncio
async def test_metadata_saml_not_authorized(mock):
    """Check handling of not SAML / OAuth unauthorized response"""

    response = AsyncMock()
    response.status = 200
    response.headers = {'content-type': 'text/html; charset=utf-8'}
    mock.return_value.__aenter__.return_value = response

    with pytest.raises(HttpError) as e_info:
        async with aiohttp.ClientSession() as client:
            await Client.build_async_client(SERVICE_URL, client)

    assert str(e_info.value).startswith('Metadata request did not return XML, MIME type:')


@patch("pyodata.client._async_fetch_metadata")
@patch('warnings.warn')
@pytest.mark.asyncio
async def test_client_custom_configuration(mock_warning, mock_fetch_metadata, metadata):
    """Check client creation for custom configuration"""

    mock_fetch_metadata.return_value = metadata

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
        async with aiohttp.ClientSession() as client:
            await Client.build_async_client(SERVICE_URL, client, config=custom_config, namespaces=namespaces)

    assert str(e_info.value) == 'You cannot pass namespaces and config at the same time'

    async with aiohttp.ClientSession() as client:
        service = await Client.build_async_client(SERVICE_URL, client, namespaces=namespaces)

    mock_warning.assert_called_with(
        'Passing namespaces directly is deprecated. Use class Config instead',
        DeprecationWarning
    )
    assert isinstance(service, pyodata.v2.service.Service)
    assert service.schema.config.namespaces == namespaces

    async with aiohttp.ClientSession() as client:
        service = await Client.build_async_client(SERVICE_URL, client, config=custom_config)

    assert isinstance(service, pyodata.v2.service.Service)
    assert service.schema.config == custom_config
