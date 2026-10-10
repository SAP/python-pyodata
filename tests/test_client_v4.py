"""Client version-dispatch tests (V2 vs V4)"""

# pylint: disable=redefined-outer-name

import asyncio

import pytest
import requests

import pyodata.v2.service
import pyodata.v4.service
from pyodata.client import Client
from pyodata.exceptions import PyODataException

URL_ROOT = 'http://odatapy.example.com'


def test_client_v4_returns_v4_service(metadata_v4):
    """Client with odata_version=4 and static metadata builds a V4 Service"""

    svc = Client(URL_ROOT, requests, odata_version=Client.ODATA_VERSION_4, metadata=metadata_v4)

    assert isinstance(svc, pyodata.v4.service.Service)
    assert type(svc).__module__ == 'pyodata.v4.service'


def test_client_v2_returns_v2_service(metadata):
    """Client with odata_version=2 and static metadata still builds a V2 Service"""

    svc = Client(URL_ROOT, requests, odata_version=Client.ODATA_VERSION_2, metadata=metadata)

    assert isinstance(svc, pyodata.v2.service.Service)
    assert type(svc).__module__ == 'pyodata.v2.service'


def test_client_default_version_is_v2(metadata):
    """Client without odata_version defaults to V2"""

    svc = Client(URL_ROOT, requests, metadata=metadata)

    assert isinstance(svc, pyodata.v2.service.Service)


def test_client_unknown_version_raises(metadata):
    """Client with an unsupported odata_version raises PyODataException"""

    with pytest.raises(PyODataException):
        Client(URL_ROOT, requests, odata_version=99, metadata=metadata)


def test_build_async_client_v4(metadata_v4):
    """build_async_client with static metadata builds a V4 Service without awaiting the connection"""

    svc = asyncio.run(
        Client.build_async_client(URL_ROOT, requests, odata_version=Client.ODATA_VERSION_4, metadata=metadata_v4))

    assert isinstance(svc, pyodata.v4.service.Service)
    assert type(svc).__module__ == 'pyodata.v4.service'


def test_odata_version_constants():
    """OData version constants have their documented values"""

    assert Client.ODATA_VERSION_2 == 2
    assert Client.ODATA_VERSION_4 == 4
