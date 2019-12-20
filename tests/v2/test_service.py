"""Service tests"""

import datetime
import responses
import requests
import pytest
from unittest.mock import patch

import pyodata.v2.service
from pyodata.exceptions import PyODataException, HttpError, ExpressionError, PyODataModelError
from pyodata.v2.service import EntityKey, EntityProxy, GetEntitySetFilter

from tests.v2.conftest import assert_request_contains_header


URL_ROOT = 'http://odatapy.example.com'


@pytest.fixture
def service(schema):
    """Service fixture"""
    assert schema.namespaces   # this is pythonic way how to check > 0
    return pyodata.v2.service.Service(URL_ROOT, schema, requests)


@responses.activate
def test_create_entity(service):
    """Basic test on creating entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/MasterEntities".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Key': '12345',
            'Data': 'abcd'
        }},
        status=201)

    result = service.entity_sets.MasterEntities.create_entity().set(**{'Key': '1234', 'Data': 'abcd'}).execute()

    assert result.Key == '12345'
    assert result.Data == 'abcd'


@responses.activate
def test_create_entity_code_201(service):
    """Creating entity returns code 201"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/MasterEntities".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Key': '12345',
            'Data': 'abcd'
        }},
        status=200)

    result = service.entity_sets.MasterEntities.create_entity(200).set(**{'Key': '1234', 'Data': 'abcd'}).execute()

    assert result.Key == '12345'
    assert result.Data == 'abcd'


@responses.activate
def test_create_entity_code_400(service):
    """Test that exception is raised in case of incorrect return code"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/MasterEntities".format(service.url),
        headers={'Content-type': 'application/json'},
        json={},
        status=400)

    with pytest.raises(PyODataException) as e_info:
        service.entity_sets.MasterEntities.create_entity().set(**{'Key': '1234', 'Data': 'abcd'}).execute()

    assert str(e_info.value).startswith('HTTP POST for Entity Set')


@responses.activate
def test_create_entity_nested(service):
    """Basic test on creating entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/Cars".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Name': 'Hadraplan',
        }},
        status=201)

    responses.add(
        responses.GET,
        "{0}/Cars('Hadraplan')/IDPic/$value/".format(service.url),
        headers={'Content-type': 'application/jpeg'},
        body='DEADBEEF',
        status=200)

    entity = {'Name': 'Hadraplan', 'IDPic' : {'Content': 'DEADBEEF'}}
    result = service.entity_sets.Cars.create_entity().set(**entity).execute()

    assert result.Name == 'Hadraplan'
    assert result.nav('IDPic').get_value().execute().content == b'DEADBEEF'


@responses.activate
def test_create_entity_header_x_requested_with(service):
    """Test for header with item X-Requested-With in create entity request"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/Cars".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Name': 'Hadraplan',
        }},
        status=201)

    entity = {'Name': 'Hadraplan'}
    result = service.entity_sets.Cars.create_entity().set(**entity).execute()

    assert result.Name == 'Hadraplan'
    assert_request_contains_header(responses.calls[0].request.headers, 'X-Requested-With', 'X')


@responses.activate
def test_create_entity_nested_list(service):
    """Test for creating entity with nested list"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/Cars".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Name': 'Hadraplan',
            'IDPic': [{
                'CarName': 'Hadraplan-Plus'
            }]
        }},
        status=201)

    entity = {'Name': 'Hadraplan', 'IDPic' : [{'CarName': 'Hadraplan-Plus'}]}
    result = service.entity_sets.Cars.create_entity().set(**entity).execute()

    assert responses.calls[0].request.body == '{"Name": "Hadraplan", "IDPic": [{"CarName": "Hadraplan-Plus"}]}'

@responses.activate
def test_get_entity_property(service):
    """Basic test on getting single property of selected entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/MasterEntities('12345')".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    assert service.entity_sets.MasterEntities.get_entity('12345').execute().Key == '12345'


@responses.activate
def test_entity_url(service):
    """Test correct build of entity url"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/MasterEntities('12345')".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    entity = service.entity_sets.MasterEntities.get_entity('12345').execute()
    assert entity.url == URL_ROOT + "/MasterEntities('12345')"


@responses.activate
def test_entity_entity_set_name(service):
    """Test correct entity set name"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/MasterEntities('12345')".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    entity = service.entity_sets.MasterEntities.get_entity('12345').execute()
    assert entity.entity_set.name == "MasterEntities"


@responses.activate
def test_entity_key_simple(service):
    """Test simple key of entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/MasterEntities('12345')".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    entity = service.entity_sets.MasterEntities.get_entity('12345').execute()
    assert len(entity.entity_key.key_properties) == 1
    assert entity.entity_key.key_properties[0].name == 'Key'


@responses.activate
def test_entity_key_complex(service):
    """Test complex key of entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'sensor1',
            'Date': "/Date(1514138400000)/"
        }},
        status=200)

    entity_key = {
        'Sensor': 'sensor1',
        'Date': datetime.datetime(2017, 12, 24, 18, 0)
    }
    key_properties = set(entity_key.keys())

    entity = service.entity_sets.TemperatureMeasurements.get_entity(key=None, **entity_key).execute()
    assert key_properties == set(entity_property.name for entity_property in  entity.entity_key.key_properties)
    # check also python represantation of date
    assert entity.Date == datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc)


def test_get_entity_property_complex_key(service):
    """Check identification of entity with key consisting of multiple properites"""

    # pylint: disable=redefined-outer-name

    with pytest.raises(PyODataException) as e_info:
        service.entity_sets.TemperatureMeasurements.get_entity('12345')

    assert str(e_info.value).startswith('Key of entity type')


def test_entity_key_simple_valid(service):
    """Test valid single value for simple key"""

    # pylint: disable=redefined-outer-name

    key = EntityKey(
        service.schema.entity_type('MasterEntity'),
        '1')

    assert key.to_key_string() == "('1')"


def test_entity_key_simple_named_valid(service):
    """Test valid single named value for simple key"""

    key = EntityKey(
        service.schema.entity_type('MasterEntity'),
        Key='1')

    assert key.to_key_string() == "(Key='1')"


def test_entity_key_simple_named_invalid(service):
    """Test invalid single named value for simple key"""

    with pytest.raises(PyODataException) as e_info:
        EntityKey(
            service.schema.entity_type('MasterEntity'),
            XXX='1')

    assert str(e_info.value).startswith('Missing value for key property Key')


def test_entity_key_complex_valid(service):
    """Test valid creationg of complex key"""

    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1', Date=datetime.datetime(2017, 12, 24, 18, 0))

    assert key.to_key_string() == "(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"


def test_entity_key_complex_single_value(service):
    """Test rejection of single value for complex key"""

    with pytest.raises(PyODataException) as e_info:
        EntityKey(
            service.schema.entity_type('TemperatureMeasurement'),
            1)

    assert str(e_info.value).startswith('Key of entity type')


@responses.activate
def test_function_import_primitive(service):
    """Simple function call with primitive return type"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/sum?A=2&B=4".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': 6},
        status=200)

    result = service.functions.sum.parameter('A', 2).parameter('B', 4).execute()
    assert result == 6


@responses.activate
@patch('logging.Logger.warning')
def test_function_import_primitive_unexpected_status_code(mock_warning, service):
    """Simple function call should use status code 200"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/sum?A=2&B=4".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': 6},
        status=201)

    result = service.functions.sum.parameter('A', 2).parameter('B', 4).execute()
    mock_warning.assert_called_with(
        'The Function Import %s has replied with HTTP Status Code %d instead of 200',
        'sum', 201)


@responses.activate
def test_function_import_without_return_type(service):
    """A simple function call without return type"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=204)

    result = service.functions.refresh.execute()
    assert result is None


@responses.activate
@patch('logging.Logger.warning')
def test_function_import_without_return_type_wrong_code(mock_warning, service):
    """A simple function call without return type should use status code 204"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=200)

    result = service.functions.refresh.execute()
    assert result is None

    mock_warning.assert_called_with(
        'The No Return Function Import %s has replied with HTTP Status Code %d instead of 204',
        'refresh', 200)


@responses.activate
@patch('logging.Logger.warning')
def test_function_import_without_return_type_wrong_code(mock_warning, service):
    """A simple function call without return type should not return any data"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        body=b'unexpected',
        status=204)

    result = service.functions.refresh.execute()
    assert result is None

    mock_warning.assert_called_with(
        'The No Return Function Import %s has returned content:\n%s',
        'refresh', 'unexpected')


@responses.activate
def test_function_import_http_redirect(service):
    """Function Imports do not support Redirects"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=300)

    with pytest.raises(HttpError) as caught:
        service.functions.refresh.execute()

    assert str(caught.value) == 'Function Import refresh requires Redirection which is not supported'


@responses.activate
def test_function_import_http_bad_request(service):
    """Function Imports report user friendly error message for Bad Requests"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=400)

    with pytest.raises(HttpError) as caught:
        service.functions.refresh.execute()

    assert str(caught.value) == 'Function Import refresh call has failed with status code 400'


@responses.activate
def test_function_import_http_sever_error(service):
    """Function Imports report user friendly error message for Server Errors"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=500)

    with pytest.raises(HttpError) as caught:
        service.functions.refresh.execute()

    assert str(caught.value) == 'Server has encountered an error while processing Function Import refresh'


@responses.activate
def test_function_import_http_not_authorized(service):
    """Function Imports report user friendly error message for Not Authorized"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=401)

    with pytest.raises(HttpError) as caught:
        service.functions.refresh.execute()

    assert str(caught.value) == 'Not authorized to call Function Import refresh'


@responses.activate
def test_function_import_http_forbidden(service):
    """Function Imports report user friendly error message for Forbidden"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=403)

    with pytest.raises(HttpError) as caught:
        service.functions.refresh.execute()

    assert str(caught.value) == 'Missing privileges to call Function Import refresh'


@responses.activate
def test_function_import_http_forbidden(service):
    """Function Imports report user friendly error message for Not Allowed"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/refresh".format(service.url),
        status=405)

    with pytest.raises(HttpError) as caught:
        service.functions.refresh.execute()

    assert str(caught.value) == 'Despite definition Function Import refresh does not support HTTP GET'


@responses.activate
def test_function_import_entity(service):
    """Function call with entity return type"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        '{0}/get_max'.format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'Sensor-address',
            'Date': "/Date(1516614510000)/",
            'Value': 456.8
        }},
        status=200)

    result = service.functions.get_max.execute()
    assert isinstance(result, pyodata.v2.service.EntityProxy)
    assert result.Sensor == 'Sensor-address'
    assert result.Value == 456.8


@responses.activate
def test_update_entity(service):
    """Check updating of entity properties"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.PATCH,
        "{0}/TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')".format(service.url),
        json={'d': {
            'Sensor': 'Sensor-address',
            'Date': "/Date(1714138400000)/",
            'Value': 34
        }},
        status=204)

    request = service.entity_sets.TemperatureMeasurements.update_entity(
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0))

    assert isinstance(request, pyodata.v2.service.EntityModifyRequest)

    request.set(Value=34)
    # Tests if update entity correctly calls 'to_json' method
    request.set(Date=datetime.datetime(2017, 12, 24, 19, 0))

    assert request._values['Value'] == 34
    assert request._values['Date'] == '/Date(1514142000000)/'

    # If preformatted datetime is passed (e. g. you already replaced datetime instance with string which is
    # complaint with odata specification), 'to_json' does not update given value (for backward compatibility reasons)
    request.set(Date='/Date(1714138400000)/')
    assert request._values['Date'] == '/Date(1714138400000)/'

    request.execute()


@responses.activate
def test_delete_entity(service):
    """Check deleting of entity"""

    responses.add(responses.DELETE, f"{service.url}/Employees(23)", status=204)
    request = service.entity_sets.Employees.delete_entity(23)

    assert isinstance(request, pyodata.v2.service.EntityDeleteRequest)
    assert request.execute() is None


@responses.activate
def test_delete_entity_with_key(service):
    """Check deleting of entity with key"""

    responses.add(responses.DELETE, f"{service.url}/Employees(ID=23)", status=204)
    key = EntityKey(service.schema.entity_type('Employee'), ID=23)
    request = service.entity_sets.Employees.delete_entity(key=key)

    assert isinstance(request, pyodata.v2.service.EntityDeleteRequest)
    assert request.execute() is None


@responses.activate
def test_delete_entity_http_error(service):
    """Check if error is raisen when deleting unknown entity"""

    responses.add(responses.DELETE, f"{service.url}/Employees(ID=23)", status=404)
    key = EntityKey(service.schema.entity_type('Employee'), ID=23)
    request = service.entity_sets.Employees.delete_entity(key=key)

    assert isinstance(request, pyodata.v2.service.EntityDeleteRequest)

    with pytest.raises(HttpError) as caught_ex:
        request.execute()

    assert str(caught_ex.value).startswith('HTTP POST for Entity delete')
    assert caught_ex.value.response.status_code == 404


def test_update_entity_with_entity_key(service):
    """Make sure the method update_entity handles correctly the parameter key which is EntityKey"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key)
    assert query.get_path() == "TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"


def test_get_entity_with_entity_key_and_other_params(service):
    """Make sure the method update_entity handles correctly the parameter key which is EntityKey"""

    # pylint: disable=redefined-outer-name

    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key=key, Foo='Bar')
    assert query.get_path() == "TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"

@responses.activate
def test_navigation_multi(service):
    """Get entities via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)/Addresses".format(service.url),
        json={'d': {
            'results': [
                {
                    'ID': 456,
                    'Street': 'Baker Street',
                    'City': 'London'
                },{
                    'ID': 457,
                    'Street': 'Lowth Road',
                    'City': 'London'
                },{
                    'ID': 458,
                    'Street': 'Warner Road',
                    'City': 'London'
                }
            ]
        }},
        status=200)

    request = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()

    assert isinstance(request, pyodata.v2.service.QueryRequest)

    addrs = request.execute()
    assert addrs[0].ID == 456
    assert addrs[0].Street == 'Baker Street'
    assert addrs[0].City == 'London'
    assert addrs[1].ID == 457
    assert addrs[1].Street == 'Lowth Road'
    assert addrs[1].City == 'London'
    assert addrs[2].ID == 458
    assert addrs[2].Street == 'Warner Road'
    assert addrs[2].City == 'London'


@responses.activate
def test_navigation(service):
    """Check getting entity via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)/Addresses(456)".format(service.url),
        json={'d': {
            'ID': 456,
            'Street': 'Baker Street',
            'City': 'London'
        }},
        status=200)

    request = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entity(456)

    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    addr = request.execute()
    assert addr.ID == 456
    assert addr.Street == 'Baker Street'
    assert addr.City == 'London'


@responses.activate
def test_navigation_1on1(service):
    """Check getting entity via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Cars('Hadraplan')/IDPic".format(service.url),
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'CarName': 'Hadraplan',
            'Content': 'DEADBEAF',
            }
        },
        status=200)

    request = service.entity_sets.Cars.get_entity('Hadraplan').nav('IDPic')
    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    idpic_proxy = request.execute()
    assert isinstance(idpic_proxy, pyodata.v2.service.NavEntityProxy)

    assert idpic_proxy.entity_set._name == 'Cars'
    assert idpic_proxy._entity_type.name == 'CarIDPic'

    assert idpic_proxy.CarName == 'Hadraplan'
    assert idpic_proxy.Content == 'DEADBEAF'


@responses.activate
def test_navigation_1on1_get_value_without_proxy(service):
    """Check getting $value via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Cars('Hadraplan')/IDPic/$value/".format(service.url),
        headers={'Content-type': 'application/jpeg'},
        body='DEADBEAF',
        status=200)

    request = service.entity_sets.Cars.get_entity('Hadraplan').nav('IDPic').get_value()
    assert isinstance(request, pyodata.v2.service.ODataHttpRequest)

    stream = request.execute()
    assert stream.content == b'DEADBEAF'


@responses.activate
def test_navigation_when_nes_in_another_ns(service):
    """Check whether it is possible to navigate when AssociationSet is defined
       in a different namespace.
   """

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Customers('Mammon')/Orders".format(service.url),
        json={'d': {'results' : [{
            'Number': '456',
            'Owner': 'Mammon',
        }]}},
        status=200)

    request = service.entity_sets.Customers.get_entity('Mammon').nav('Orders').get_entities()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    orders = request.execute()

    assert len(orders) == 1

    assert orders[0].Number == '456'
    assert orders[0].Owner == 'Mammon'


@responses.activate
def test_entity_get_value_1on1_with_proxy(service):
    """Check getting $value"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Cars('Hadraplan')/IDPic".format(service.url),
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'CarName': 'Hadraplan',
            'Content': 'DEADBEAF',
            }
        },
        status=200)

    responses.add(
        responses.GET,
        "{0}/Cars('Hadraplan')/IDPic/$value/".format(service.url),
        headers={'Content-type': 'application/jpeg'},
        body='DEADBEAF',
        status=200)

    request = service.entity_sets.Cars.get_entity('Hadraplan').nav('IDPic').execute().get_value()
    assert isinstance(request, pyodata.v2.service.ODataHttpRequest)

    stream = request.execute()
    assert stream.content == b'DEADBEAF'


@responses.activate
def test_entity_get_value_without_proxy(service):
    """Check getting $value without proxy"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/CarIDPics('Hadraplan')/$value/".format(service.url),
        headers={'Content-type': 'application/jpeg'},
        body='DEADBEAF',
        status=200)

    request = service.entity_sets.CarIDPics.get_entity('Hadraplan').get_value()
    assert isinstance(request, pyodata.v2.service.ODataHttpRequest)

    stream = request.execute()
    assert stream.content == b'DEADBEAF'


@responses.activate
def test_entity_get_value_with_proxy(service):
    """Check getting $value with proxy"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/CarIDPics('Hadraplan')".format(service.url),
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'CarName': 'Hadraplan',
            'Content': 'DEADBEAF',
            }
        },
        status=200)

    responses.add(
        responses.GET,
        "{0}/CarIDPics('Hadraplan')/$value/".format(service.url),
        headers={'Content-type': 'application/jpeg'},
        body='DEADBEAF',
        status=200)

    request = service.entity_sets.CarIDPics.get_entity('Hadraplan').execute().get_value()
    assert isinstance(request, pyodata.v2.service.ODataHttpRequest)

    stream = request.execute()
    assert stream.content == b'DEADBEAF'


@responses.activate
def test_entity_get_value_without_proxy_error(service):
    """Check getting $value without proxy"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/CarIDPics('Hadraplan')/$value/".format(service.url),
        headers={'Content-type': 'text/plain'},
        body='Internal Server Error',
        status=500)

    with pytest.raises(HttpError) as caught_ex:
        service.entity_sets.CarIDPics.get_entity('Hadraplan').get_value().execute()

    assert str(caught_ex.value).startswith('HTTP GET for $value failed with status code 500')
    assert caught_ex.value.response.status_code == 500


@responses.activate
def test_navigation_create_entity(service):
    """Check creating entity via a navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/Employees(23)/Addresses".format(service.url),
        json={'d': {
            'ID': 42,
            'Street': 'Holandska',
            'City': 'Brno'
        }},
        status=201)

    request = service.entity_sets.Employees.get_entity(23).nav('Addresses').create_entity()
    request.set(ID='42', Street='Holandska', City='Brno')

    assert isinstance(request, pyodata.v2.service.EntityCreateRequest)

    addr = request.execute()

    assert len(responses.calls) == 1

    assert addr.ID == 42
    assert addr.Street == 'Holandska'
    assert addr.City == 'Brno'


@responses.activate
def test_navigation_from_entity_multi(service):
    """Get entities via navigation property from entity proxy"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)".format(service.url),
        json={'d': {
            'ID': 23,
            'NameFirst': 'Rob',
            'NameLast': 'Ickes'
        }},
        status=200)

    responses.add(
        responses.GET,
        "{0}/Employees(23)/Addresses".format(service.url),
        json={'d': {
            'results': [
                {
                    'ID': 456,
                    'Street': 'Baker Street',
                    'City': 'London'
                },{
                    'ID': 457,
                    'Street': 'Lowth Road',
                    'City': 'London'
                },{
                    'ID': 458,
                    'Street': 'Warner Road',
                    'City': 'London'
                }
            ]
        }},
        status=200)

    request = service.entity_sets.Employees.get_entity(23)

    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    emp = request.execute()

    request = emp.nav('Addresses').get_entities()

    assert isinstance(request, pyodata.v2.service.QueryRequest)

    addrs = request.execute()
    assert addrs[0].ID == 456
    assert addrs[0].Street == 'Baker Street'
    assert addrs[0].City == 'London'
    assert addrs[1].ID == 457
    assert addrs[1].Street == 'Lowth Road'
    assert addrs[1].City == 'London'
    assert addrs[2].ID == 458
    assert addrs[2].Street == 'Warner Road'
    assert addrs[2].City == 'London'


@responses.activate
def test_navigation_from_entity(service):
    """Check getting entity via navigation property from entity proxy"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)".format(service.url),
        json={'d': {
            'ID': 23,
            'NameFirst': 'Rob',
            'NameLast': 'Ickes'
        }},
        status=200)

    responses.add(
        responses.GET,
        "{0}/Employees(23)/Addresses(456)".format(service.url),
        json={'d': {
            'ID': 456,
            'Street': 'Baker Street',
            'City': 'London'
        }},
        status=200)

    request = service.entity_sets.Employees.get_entity(23)

    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    emp = request.execute()

    request = emp.nav('Addresses').get_entity(456)

    addr = request.execute()
    assert addr.ID == 456
    assert addr.Street == 'Baker Street'
    assert addr.City == 'London'


# TODO add test_get_entity_with_guid


@responses.activate
def test_get_entity(service):
    """Check getting entities"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)".format(service.url),
        json={'d': {
            'ID': 23,
            'NameFirst': 'Rob',
            'NameLast': 'Ickes'
        }},
        status=200)

    request = service.entity_sets.Employees.get_entity(23)

    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    emp = request.execute()
    assert emp.ID == 23
    assert emp.NameFirst == 'Rob'
    assert emp.NameLast == 'Ickes'


@responses.activate
def test_get_entity_expanded(service):
    """Check getting entities with expanded navigation properties"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)".format(service.url),
        json={'d': {
            'ID': 23,
            'NameFirst': 'Rob',
            'NameLast': 'Ickes',
            'Addresses': {
                "results": [
                    {
                        'ID': 456,
                        'Street': 'Baker Street',
                        'City': 'London'
                    }
                ]
            }
        }},
        status=200)

    request = service.entity_sets.Employees.get_entity(23)
    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    emp = request.expand('Addresses').execute()

    assert emp.ID == 23
    assert emp.NameFirst == 'Rob'
    assert emp.NameLast == 'Ickes'

    assert emp.Addresses[0].ID == 456
    assert emp.Addresses[0].Street == 'Baker Street'
    assert emp.Addresses[0].City == 'London'


@responses.activate
def test_batch_request(service):
    """Batch requests"""

    # pylint: disable=redefined-outer-name

    response_body = (b'--batch_r1\n'
                     b'Content-Type: application/http\n'
                     b'Content-Transfer-Encoding: binary\n'
                     b'\n'
                     b'HTTP/1.1 200 OK\n'
                     b'Content-Type: application/json\n'
                     b'\n'
                     b'{"d": {"ID": 23, "NameFirst": "Rob", "NameLast": "Ickes", "Address": { "ID": 456, "Street": "Baker Street", "City": "London"} }}'
                     b'\n'
                     b'--batch_r1\n'
                     b'Content-Type: multipart/mixed; boundary=changeset_1\n'
                     b'\n'
                     b'--changeset_1\n'
                     b'Content-Type: application/http\n'
                     b'Content-Transfer-Encoding: binary\n'
                     b'\n'
                     b'HTTP/1.1 204 Updated\n'
                     b'Content-Type: application/json\n'
                     b'\n'
                     b"{b'd': {'Sensor': 'Sensor-address', 'Date': datetime\'2017-12-24T18:00\', 'Value': 34}}"
                     b'\n'
                     b'--changeset_1--\n'
                     b'\n'
                     b'--batch_r1--')

    responses.add(
        responses.POST,
        '{0}/$batch'.format(URL_ROOT),
        body=response_body,
        content_type='multipart/mixed; boundary=batch_r1',
        status=202)

    batch = service.create_batch('batch1')

    chset = service.create_changeset('chset1')

    employee_request = service.entity_sets.Employees.get_entity(23)

    temp_request = service.entity_sets.TemperatureMeasurements.update_entity(
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0)).set(Value=34)

    batch.add_request(employee_request)

    chset.add_request(temp_request)

    batch.add_request(chset)

    response = batch.execute()

    assert len(response) == 2

    employee_response = response[0]
    assert isinstance(employee_response, pyodata.v2.service.EntityProxy)

    chset_response = response[1]
    assert isinstance(chset_response, list)
    assert len(chset_response) == 1
    assert chset_response[0] is None   # response to update request is None


@responses.activate
def test_batch_request_failed_changeset(service):
    """Check single response for changeset"""

    # pylint: disable=redefined-outer-name

    response_body = ('--batch_r1\n'
                     'Content-Type: application/http\n'
                     'Content-Transfer-Encoding: binary\n'
                     '\n'
                     'HTTP/1.1 400 Bad Request\n'
                     'Content-Type: application/json;charset=utf-8'
                     ''
                     '{"error": "this is error description"}'
                     '--batch_r1--')

    responses.add(
        responses.POST,
        '{0}/$batch'.format(URL_ROOT),
        body=response_body,
        content_type='multipart/mixed; boundary=batch_r1',
        status=202)

    batch = service.create_batch('batch1')

    chset = service.create_changeset('chset1')

    employee_request1 = service.entity_sets.Employees.get_entity(23)
    employee_request2 = service.entity_sets.Employees.get_entity(23)

    chset.add_request(employee_request1)
    chset.add_request(employee_request2)

    batch.add_request(chset)

    with pytest.raises(HttpError) as e_info:
        batch.execute()

    assert str(e_info.value).startswith('Changeset cannot be processed')
    assert isinstance(e_info.value, HttpError)
    assert e_info.value.response.status_code == 400


def test_get_entity_with_entity_key(service):
    """Make sure the method get_entity handles correctly the parameter key which is EntityKey"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0))

    query = service.entity_sets.TemperatureMeasurements.get_entity(key)
    assert query.get_path() == "TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"


def test_get_entity_with_entity_key_and_other_params(service):
    """Make sure the method get_entity handles correctly the parameter key which is EntityKey"""

    # pylint: disable=redefined-outer-name

    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0))

    query = service.entity_sets.TemperatureMeasurements.get_entity(key=key, Foo='Bar')
    assert query.get_path() == "TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"


def test_entity_proxy_equals(service):
    """Two entity proxies are equal if they hold the same data"""

    properties = {'Key': 'a', 'DataType': 'b', 'Data': 'c', 'DataName': 'd'}
    fst_entity = EntityProxy(service, service.entity_sets.MasterEntities,
                             service.schema.entity_type('MasterEntity'), properties)
    scn_entity = EntityProxy(service, service.entity_sets.MasterEntities,
                             service.schema.entity_type('MasterEntity'), properties)

    properties['DataType'] = 'g'
    thr_entity = EntityProxy(service, service.entity_sets.MasterEntities,
                             service.schema.entity_type('MasterEntity'), properties)

    assert fst_entity.equals(fst_entity)

    assert fst_entity.equals(scn_entity)
    assert scn_entity.equals(fst_entity)

    assert not fst_entity.equals(thr_entity)
    assert not scn_entity.equals(thr_entity)


def test_get_entity_set_query_filter_eq(service):
    """Test the operator 'eq' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.MasterEntities.get_entities()
    filter_str = request.Key == 'foo'

    assert filter_str == "Key eq 'foo'"


def test_get_entity_set_query_filter_ne(service):
    """Test the operator 'ne' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.MasterEntities.get_entities()
    filter_str = request.Key != 'bar'

    assert filter_str == "Key ne 'bar'"


def test_get_entity_set_query_filter_and(service):
    """Test the operator 'and' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.MasterEntities.get_entities()

    filter_str = GetEntitySetFilter.and_(request.Key == 'bar', request.DataType != 'foo')

    assert filter_str == "(Key eq 'bar' and DataType ne 'foo')"

    with pytest.raises(ExpressionError) as e_info:
        GetEntitySetFilter.and_()
    assert e_info.value.args[0] == 'The $filter operator \'and\' needs at least two operands'

    with pytest.raises(ExpressionError) as e_info:
        GetEntitySetFilter.and_('foo')
    assert e_info.value.args[0] == 'The $filter operator \'and\' needs at least two operands'


def test_get_entity_set_query_filter_or(service):
    """Test the operator 'and' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.MasterEntities.get_entities()

    filter_str = GetEntitySetFilter.or_(request.Key == 'bar', request.DataType != 'foo')

    assert filter_str == "(Key eq 'bar' or DataType ne 'foo')"

    with pytest.raises(ExpressionError) as e_info:
        GetEntitySetFilter.or_()
    assert e_info.value.args[0] == 'The $filter operator \'or\' needs at least two operands'

    with pytest.raises(ExpressionError) as e_info:
        GetEntitySetFilter.or_('foo')
    assert e_info.value.args[0] == 'The $filter operator \'or\' needs at least two operands'


def test_get_entity_set_query_filter_property_error(service):
    """Test the operator 'and' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.MasterEntities.get_entities()

    with pytest.raises(PyODataModelError) as e_info:
        assert not request.Foo == 'bar'
    assert e_info.value.args[0] == 'Property Foo not found on EntityType(MasterEntity)'


@responses.activate
def test_count(service):
    """Check getting $count"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees/$count".format(service.url),
        json=23,
        status=200)

    request = service.entity_sets.Employees.get_entities().count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 23


@responses.activate
def test_count_with_skip(service):
    """Check getting $count with $skip"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees/$count?$skip=12".format(service.url),
        json=11,
        status=200)

    request = service.entity_sets.Employees.get_entities().skip(12).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 11


@responses.activate
def test_navigation_count(service):
    """Check getting $count via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)/Addresses/$count".format(service.url),
        json=458,
        status=200)

    addresses = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()
    request = addresses.count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 458


@responses.activate
def test_navigation_count_with_filter(service):
    """Check getting $count via navigation property with $filter"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        "{0}/Employees(23)/Addresses/$count?$filter=City eq 'London'".format(service.url),
        json=3,
        status=200)

    addresses = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()
    request = addresses.filter(addresses.City == 'London').count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_create_entity_with_datetime(service):
    """
        Basic test on creating entity with datetime
        Also tzinfo is set to simulate user passing datetime object with different timezone than UTC
    """

    # https://stackoverflow.com/questions/17976063/how-to-create-tzinfo-when-i-have-utc-offset
    class MyUTCOffsetTimezone(datetime.tzinfo):

        def __init__(self, offset=19800, name=None):
            self.offset = datetime.timedelta(seconds=offset)
            self.name = name or self.__class__.__name__

        def utcoffset(self, dt):
            return self.offset

        def tzname(self, dt):
            return self.name

        def dst(self, dt):
            return datetime.timedelta(0)

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/TemperatureMeasurements".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'Sensor1',
            'Date': '/Date(1514138400000)/',
            'Value': '34'
        }},
        status=201)


    # Offset -18000 sec is for America/Chicago (CDT) timezone
    request = service.entity_sets.TemperatureMeasurements.create_entity().set(**{
        'Sensor': 'Sensor1',
        'Date': datetime.datetime(2017, 12, 24, 18, 0, tzinfo=MyUTCOffsetTimezone(-18000)),
        'Value': 34
    })

    assert request._values['Date'] == '/Date(1514138400000)/'

    result = request.execute()
    assert result.Date == datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc)


@responses.activate
def test_parsing_of_datetime_before_unix_time(service):
    """Test DateTime handling of time before 1970"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        "{0}/TemperatureMeasurements".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'Sensor1',
            'Date': '/Date(-777877200000)/',
            'Value': '34'
        }},
        status=201)

    request = service.entity_sets.TemperatureMeasurements.create_entity().set(**{
        'Sensor': 'Sensor1',
        'Date': datetime.datetime(1945, 5, 8, 19, 0),
        'Value': 34
    })

    assert request._values['Date'] == '/Date(-777877200000)/'

    result = request.execute()
    assert result.Date == datetime.datetime(1945, 5, 8, 19, 0, tzinfo=datetime.timezone.utc)
