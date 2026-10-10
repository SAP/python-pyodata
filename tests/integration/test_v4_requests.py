"""Integration round-trip tests for OData V4 via the Requests library.

   These build the service through the real pyodata.Client entry point and
   exercise it end-to-end with the ``responses`` HTTP mock.
"""

# pylint: disable=redefined-outer-name

import responses
import requests

import pyodata
import pyodata.v4.service
from pyodata.client import Client

SERVICE_URL = 'http://example.com'


@responses.activate
def test_v4_requests_get_entities(metadata_v4):
    """Client(odata_version=4) + get_entities round-trips flat V4 JSON over requests"""

    client = pyodata.Client(SERVICE_URL, requests, odata_version=Client.ODATA_VERSION_4, metadata=metadata_v4)
    assert isinstance(client, pyodata.v4.service.Service)

    responses.add(
        responses.GET,
        f"{SERVICE_URL}/Products",
        content_type='application/json',
        json={
            '@odata.count': 2,
            'value': [
                {'ID': 1, 'Name': 'Chai'},
                {'ID': 2, 'Name': 'Chang'},
            ],
        },
        status=200)

    result = client.entity_sets.Products.get_entities().execute()

    assert len(result) == 2
    assert result[0].ID == 1
    assert result[0].Name == 'Chai'
    assert result[1].ID == 2
    assert result[1].Name == 'Chang'

    assert responses.calls[0].request.headers['OData-Version'] == '4.0'


@responses.activate
def test_v4_requests_create_entity(metadata_v4):
    """Client(odata_version=4) + create_entity round-trips a POST 201 over requests"""

    client = pyodata.Client(SERVICE_URL, requests, odata_version=Client.ODATA_VERSION_4, metadata=metadata_v4)
    assert isinstance(client, pyodata.v4.service.Service)

    responses.add(
        responses.POST,
        f"{SERVICE_URL}/Products",
        content_type='application/json',
        headers={'ETag': 'W/"etag-10"'},
        json={
            '@odata.etag': 'W/"etag-10"',
            'ID': 10,
            'Name': 'Tofu',
        },
        status=201)

    result = client.entity_sets.Products.create_entity().set(ID=10, Name='Tofu').execute()

    assert result.ID == 10
    assert result.Name == 'Tofu'
    assert result.etag == 'W/"etag-10"'
    assert responses.calls[0].request.method == 'POST'
