"""OData V4 service layer tests"""

# pylint: disable=redefined-outer-name

import responses
import requests
import pytest
from urllib.parse import quote
from unittest import mock

import pyodata.v4.service
import pyodata.v2.service
from pyodata.exceptions import HttpError, PyODataException
from pyodata.v4.service import (
    EntityKey,
    EntityModifyRequest,
    FunctionRequest,
    ActionRequest,
    ListWithTotalCount,
    encode_multipart,
)

from tests.conftest import assert_request_contains_header


URL_ROOT = 'http://odatapy.example.com'


@pytest.fixture
def service(schema_v4):
    """V4 Service fixture"""
    assert schema_v4.entity_sets   # pythonic truthiness check for > 0
    return pyodata.v4.service.Service(URL_ROOT, schema_v4, requests)


@responses.activate
def test_get_entity_flat_json_and_etag(service):
    """get_entity parses flat V4 JSON (no 'd' wrapper) and the @odata.etag body annotation"""

    responses.add(
        responses.GET,
        f"{service.url}/{quote('Products(1)')}",
        headers={'Content-type': 'application/json'},
        json={
            '@odata.context': f'{service.url}/$metadata#Products/$entity',
            '@odata.etag': 'W/"etag-42"',
            '@odata.id': f'{service.url}/Products(1)',
            'ID': 1,
            'Name': 'Chai',
            'Rating': 4,
        },
        status=200)

    product = service.entity_sets.Products.get_entity(1).execute()

    assert product.ID == 1
    assert product.Name == 'Chai'
    assert product.Rating == 4
    assert product.etag == 'W/"etag-42"'
    assert product.odata_id == f'{service.url}/Products(1)'
    assert product.odata_context == f'{service.url}/$metadata#Products/$entity'

    assert_request_contains_header(responses.calls[0].request.headers, 'OData-Version', '4.0')


@responses.activate
def test_get_entities_value_count_nextlink(service):
    """get_entities surfaces the 'value' array plus @odata.count and @odata.nextLink"""

    next_link = f'{service.url}/Products?$skiptoken=2'
    responses.add(
        responses.GET,
        f"{service.url}/Products",
        headers={'Content-type': 'application/json'},
        json={
            '@odata.count': 2,
            '@odata.nextLink': next_link,
            'value': [
                {'ID': 1, 'Name': 'Chai'},
                {'ID': 2, 'Name': 'Chang'},
            ],
        },
        status=200)

    result = service.entity_sets.Products.get_entities().execute()

    assert isinstance(result, ListWithTotalCount)
    assert result.total_count == 2
    assert result.next_url == next_link
    assert len(result) == 2
    assert result[0].Name == 'Chai'
    assert result[1].ID == 2


@responses.activate
def test_create_entity_happy_path(service):
    """create_entity POST 201 returns a proxy built from flat JSON"""

    responses.add(
        responses.POST,
        f"{service.url}/Products",
        headers={'Content-type': 'application/json'},
        json={'ID': 10, 'Name': 'Tofu'},
        status=201)

    result = service.entity_sets.Products.create_entity().set(ID=10, Name='Tofu').execute()

    assert result.ID == 10
    assert result.Name == 'Tofu'
    assert responses.calls[0].request.method == 'POST'


@responses.activate
def test_create_entity_error_path(service):
    """create_entity raises HttpError on a non-201 status"""

    responses.add(
        responses.POST,
        f"{service.url}/Products",
        headers={'Content-type': 'application/json'},
        json={},
        status=400)

    with pytest.raises(HttpError) as e_info:
        service.entity_sets.Products.create_entity().set(ID=10, Name='Tofu').execute()

    assert str(e_info.value).startswith('HTTP POST for Entity Set')


@responses.activate
def test_update_entity_uses_patch(service):
    """update_entity defaults to PATCH (V4) and sends a JSON body"""

    responses.add(
        responses.PATCH,
        f"{service.url}/{quote('Products(1)')}",
        status=204)

    service.entity_sets.Products.update_entity(1).set(Name='Chai Updated').execute()

    assert responses.calls[0].request.method == 'PATCH'
    assert responses.calls[0].request.body == '{"Name": "Chai Updated"}'
    assert_request_contains_header(responses.calls[0].request.headers, 'Content-Type', 'application/json')


@responses.activate
def test_update_entity_error_path(service):
    """update_entity raises HttpError on an unexpected status"""

    responses.add(
        responses.PATCH,
        f"{service.url}/{quote('Products(1)')}",
        status=500)

    with pytest.raises(HttpError) as e_info:
        service.entity_sets.Products.update_entity(1).set(Name='x').execute()

    assert str(e_info.value).startswith('HTTP modify request for Entity Set')


@responses.activate
def test_delete_entity_happy_path(service):
    """delete_entity succeeds on 204 and issues a DELETE"""

    responses.add(
        responses.DELETE,
        f"{service.url}/{quote('Products(1)')}",
        status=204)

    service.entity_sets.Products.delete_entity(1).execute()

    assert responses.calls[0].request.method == 'DELETE'


@responses.activate
def test_delete_entity_error_path(service):
    """delete_entity raises HttpError when the service does not reply 204"""

    responses.add(
        responses.DELETE,
        f"{service.url}/{quote('Products(1)')}",
        status=404)

    with pytest.raises(HttpError) as e_info:
        service.entity_sets.Products.delete_entity(1).execute()

    assert str(e_info.value).startswith('HTTP POST for Entity delete')


@responses.activate
def test_nav_without_contains_target(service):
    """nav('Category') (no ContainsTarget) resolves to a single-entity GET at Products(1)/Category"""

    responses.add(
        responses.GET,
        f"{service.url}/{quote('Products(1)')}/Category",
        headers={'Content-type': 'application/json'},
        json={'ID': 7, 'Name': 'Beverages'},
        status=200)

    category = service.entity_sets.Products.get_entity(1).nav('Category').execute()

    assert category.ID == 7
    assert category.Name == 'Beverages'
    assert responses.calls[0].request.url.endswith('/Category')


def test_nav_with_contains_target(service):
    """nav('Supplier') targets a ContainsTarget navigation property.

    A contained target (Supplier) is addressed relative to the parent and need not
    have a backing EntitySet, so nav() must NOT consult entity_set_for_type() for it
    (that lookup would raise KeyError, as Supplier has no EntitySet). The contained
    branch resolves to an EntitySetProxy addressed relative to the parent segment.
    """

    nav_prop = service.schema.entity_type('Product').nav_proprty('Supplier')
    assert nav_prop.contains_target is True

    # Supplier has no backing EntitySet; entity_set_for_type() would raise KeyError.
    with pytest.raises(KeyError):
        service.schema.entity_set_for_type('Supplier')

    # The contained branch must resolve WITHOUT calling entity_set_for_type.
    key = EntityKey(service.schema.entity_type('Product'), 1)
    with mock.patch.object(type(service.schema), 'entity_set_for_type',
                           side_effect=AssertionError('entity_set_for_type must not be '
                                                       'called for a contained target')):
        proxy = service.entity_sets.Products.nav('Supplier', key)

    # Addressed relative to the parent: Products(1)/Supplier
    assert proxy.last_segment == 'Products(1)/Supplier'


@responses.activate
def test_function_request_v4_path_format(service):
    """FunctionImport is invoked via GET with params in the path: BestProduct(minRating=5)"""

    responses.add(
        responses.GET,
        f"{service.url}/BestProduct(minRating=5)",
        headers={'Content-type': 'application/json'},
        json={'ID': 1, 'Name': 'Chai'},
        status=200)

    request = service.functions.BestProduct.parameter('minRating', 5)
    assert isinstance(request, FunctionRequest)

    result = request.execute()

    assert result.Name == 'Chai'
    assert responses.calls[0].request.method == 'GET'
    assert responses.calls[0].request.url.endswith('/BestProduct(minRating=5)')


@responses.activate
def test_action_request_unbound_post(service):
    """ActionImport ResetAll executes end-to-end via POST with a JSON body (V4 wire format).

    ResetAll is unbound and has no ReturnType, so return_type is None and the response
    handler returns None on a 204. The request itself is a POST to /ResetAll with an empty
    JSON body and the OData-Version: 4.0 header.
    """

    responses.add(
        responses.POST,
        f"{service.url}/ResetAll",
        status=204)

    request = service.functions.ResetAll
    assert isinstance(request, ActionRequest)

    result = request.execute()

    assert result is None
    assert responses.calls[0].request.method == 'POST'
    assert responses.calls[0].request.url.endswith('/ResetAll')
    assert responses.calls[0].request.body == '{}'
    assert_request_contains_header(responses.calls[0].request.headers, 'OData-Version', '4.0')


def test_action_request_bound_path_format(service):
    """A bound action builds the path as {key}/{ActionName} via with_entity()"""

    key = EntityKey(service.schema.entity_type('Product'), 1)
    request = ActionRequest(service.url, service.connection, lambda r: r,
                            _ActionImportStub(service.schema.action('Discount')))
    request.with_entity(key)

    assert request.get_method() == 'POST'
    assert request.get_path() == '(1)/Discount'


@responses.activate
def test_singleton_get_entity_no_key(service):
    """SingletonProxy.get_entity() addresses the singleton by name only (no key predicate)"""

    responses.add(
        responses.GET,
        f"{service.url}/BestSeller/",
        headers={'Content-type': 'application/json'},
        json={'ID': 1, 'Name': 'Chai'},
        status=200)

    result = service.singletons.BestSeller.get_entity().execute()

    assert result.Name == 'Chai'
    assert responses.calls[0].request.url.rstrip('/').endswith('/BestSeller')


@responses.activate
def test_query_count_appends_count_segment(service):
    """QueryRequest.count() routes the request through the /$count path segment"""

    responses.add(
        responses.GET,
        f"{service.url}/Products/$count",
        body='2',
        status=200)

    result = service.entity_sets.Products.get_entities().count().execute()

    assert result == 2
    assert responses.calls[0].request.url.endswith('/Products/$count')


@responses.activate
def test_query_inline_count_param(service):
    """QueryRequest.count(inline=True) sends $count=true as a query parameter"""

    responses.add(
        responses.GET,
        f"{service.url}/Products",
        headers={'Content-type': 'application/json'},
        json={'@odata.count': 1, 'value': [{'ID': 1, 'Name': 'Chai'}]},
        status=200)

    result = service.entity_sets.Products.get_entities().count(inline=True).execute()

    assert result.total_count == 1
    assert '%24count=true' in responses.calls[0].request.url


@responses.activate
def test_query_search(service):
    """QueryRequest.search() emits the V4 $search query parameter"""

    responses.add(
        responses.GET,
        f"{service.url}/Products",
        headers={'Content-type': 'application/json'},
        json={'value': [{'ID': 1, 'Name': 'Chai'}]},
        status=200)

    service.entity_sets.Products.get_entities().search('Chai').execute()

    assert '%24search=Chai' in responses.calls[0].request.url


def test_merge_method_raises_value_error(service):
    """MERGE is not an allowed V4 modify method and must raise ValueError"""

    assert 'MERGE' not in EntityModifyRequest.ALLOWED_HTTP_METHODS

    with pytest.raises(ValueError):
        service.entity_sets.Products.update_entity(1, method='MERGE').set(Name='x')


def test_batch_part_headers_contain_odata_version(service):
    """Multipart batch encoding adds the OData-Version: 4.0 header to each inner request part"""

    batch = service.create_batch()
    batch.add_request(service.entity_sets.Products.get_entities())

    body = encode_multipart(batch.get_boundary(), batch.requests)

    assert 'OData-Version: 4.0' in body


def test_function_container_dispatch_types(service):
    """FunctionContainer dispatches ActionImport -> ActionRequest, FunctionImport -> FunctionRequest"""

    assert isinstance(service.functions.ResetAll, ActionRequest)
    assert isinstance(service.functions.BestProduct, FunctionRequest)


def test_shared_classes_imported_from_v2():
    """Classes with no V2/V4 differences are the very same objects imported from v2.service"""

    assert pyodata.v4.service.GetEntitySetFilter is pyodata.v2.service.GetEntitySetFilter
    assert pyodata.v4.service.ListWithTotalCount is pyodata.v2.service.ListWithTotalCount
    assert pyodata.v4.service.FilterExpression is pyodata.v2.service.FilterExpression
    assert pyodata.v4.service.ODataHttpResponse is pyodata.v2.service.ODataHttpResponse


def test_stubbed_v4_features_raise_not_implemented(service):
    """Intentionally-stubbed V4 features raise NotImplementedError"""

    with pytest.raises(NotImplementedError):
        service.create_json_batch()

    with pytest.raises(NotImplementedError):
        service.entity_reference()

    with pytest.raises(NotImplementedError):
        service.follow_delta_link()

    with pytest.raises(NotImplementedError):
        service.entity_sets.Products.get_entities().expand({'Category': {}})


class _ActionImportStub:
    """Minimal ActionImport-like object exposing .name and .action for ActionRequest tests"""

    def __init__(self, action):
        self.name = action.name
        self.action = action
