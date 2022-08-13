"""Service tests"""

import datetime
import responses
import requests
import pytest
from unittest.mock import patch

import pyodata.v2.model
import pyodata.v2.service
from pyodata.exceptions import PyODataException, HttpError, ExpressionError, ProgramError, PyODataModelError
from pyodata.v2 import model
from pyodata.v2.service import EntityKey, EntityProxy, GetEntitySetFilter, ODataHttpResponse, HTTP_CODE_OK

from tests.conftest import assert_request_contains_header, contents_of_fixtures_file


URL_ROOT = 'http://odatapy.example.com'


@pytest.fixture
def service(schema):
    """Service fixture"""
    assert schema.namespaces   # this is pythonic way how to check > 0
    return pyodata.v2.service.Service(URL_ROOT, schema, requests)


@pytest.fixture
def service_retain_null(schema):
    """Service fixture which keeps null values as such"""
    assert schema.namespaces
    return pyodata.v2.service.Service(URL_ROOT, schema, requests, model.Config(retain_null=True))


@responses.activate
def test_create_entity(service):
    """Basic test on creating entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        f"{service.url}/MasterEntities",
        headers={
            'Content-type': 'application/json',
            'ETag':  'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"'
        },
        json={'d': {
            '__metadata': {
                'etag': 'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"',
            },
            'Key': '12345',
            'Data': 'abcd'
        }},
        status=201)

    result = service.entity_sets.MasterEntities.create_entity().set(**{'Key': '1234', 'Data': 'abcd'}).execute()

    assert result.Key == '12345'
    assert result.Data == 'abcd'
    assert result.etag == 'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"'


@responses.activate
def test_create_entity_code_201(service):
    """Creating entity returns code 201"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        f"{service.url}/MasterEntities",
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
        f"{service.url}/MasterEntities",
        headers={'Content-type': 'application/json'},
        json={},
        status=400)

    with pytest.raises(PyODataException) as e_info:
        service.entity_sets.MasterEntities.create_entity().set(**{'Key': '1234', 'Data': 'abcd'}).execute()

    assert str(e_info.value).startswith('HTTP POST for Entity Set')


@responses.activate
def test_create_entity_containing_enum(service):
    """Basic test on creating entity with enum"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        f"{service.url}/EnumTests",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'CountryOfOrigin': 'USA',
        }},
        status=201)

    result = service.entity_sets.EnumTests.create_entity().set(**{'CountryOfOrigin': 'USA'}).execute()

    USA = service.schema.enum_type('Country').USA
    assert result.CountryOfOrigin == USA

    traits = service.schema.enum_type('Country').traits
    literal = traits.to_literal(USA)

    assert literal == "EXAMPLE_SRV.Country\'USA\'"
    assert traits.from_literal(literal).name == 'USA'

@responses.activate
def test_create_entity_nested(service):
    """Basic test on creating entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        f"{service.url}/Cars",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Name': 'Hadraplan',
        }},
        status=201)

    responses.add(
        responses.GET,
        f"{service.url}/Cars('Hadraplan')/IDPic/$value/",
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
        f"{service.url}/Cars",
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
        f"{service.url}/Customers",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Name': 'John',
            'Orders': [
                {'Owner': 'Mammon'},
                {'Owner': 'Tomas'},
            ]
        }},
        status=201)

    entity = {'Name': 'John', 'Orders': [{'Owner': 'Mammon'}, {'Owner': 'Tomas'}]}
    result = service.entity_sets.Customers.create_entity().set(**entity).execute()

    assert responses.calls[0].request.body == '{"Name": "John", "Orders": [{"Owner": "Mammon"}, {"Owner": "Tomas"}]}'

@responses.activate
def test_get_entity_property(service):
    """Basic test on getting single property of selected entity"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/MasterEntities('12345')",
        headers={
            'ETag': 'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"',
            'Content-type': 'application/json',
        },
        json={'d': {'Key': '12345'}},
        status=200)

    result = service.entity_sets.MasterEntities.get_entity('12345').execute()
    assert result.Key == '12345'
    assert result.etag == 'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"'


@responses.activate
def test_entity_url(service):
    """Test correct build of entity url"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/MasterEntities('12345')",
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
        f"{service.url}/MasterEntities('12345')",
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
        f"{service.url}/MasterEntities('12345')",
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
        f"{service.url}/TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'sensor1',
            'Date': "/Date(1514138400000)/"
        }},
        status=200)

    entity_key = {
        'Sensor': 'sensor1',
        'Date': datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc)
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
        Sensor='sensor1', Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

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
        f"{service.url}/sum?A=2&B=4",
        headers={'Content-type': 'application/json'},
        json={'d': 6},
        status=200)

    result = service.functions.sum.parameter('A', 2).parameter('B', 4).execute()
    assert result == 6


@responses.activate
def test_function_import_escape_parameter(service):
    """Simple function call with special URL characters in parameter value"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/retrieve?Param=%27%26|%2B|%3D|%2F|%3F|+|%40%27",
        headers={'Content-type': 'application/json'},
        json={'d': True},
        status=200)

    chars = "|".join("&+=/? @")
    result = service.functions.retrieve.parameter('Param', chars).execute()
    assert result is True



@responses.activate
@patch('logging.Logger.warning')
def test_function_import_primitive_unexpected_status_code(mock_warning, service):
    """Simple function call should use status code 200"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/sum?A=2&B=4",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f"{service.url}/refresh",
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
        f'{service.url}/get_max',
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'Sensor-address',
            'Date': "/Date(1516614510000)/",
            'Value': '456.8d'
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
        f"{service.url}/TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')",
        json={'d': {
            'Sensor': 'Sensor-address',
            'Date': "/Date(1714138400000)/",
            'Value': '34.0d'
        }},
        status=204)

    request = service.entity_sets.TemperatureMeasurements.update_entity(
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    assert isinstance(request, pyodata.v2.service.EntityModifyRequest)

    request.set(Value=34.0)
    # Tests if update entity correctly calls 'to_json' method
    request.set(Date=datetime.datetime(2017, 12, 24, 19, 0, tzinfo=datetime.timezone.utc))

    assert request._values['Value'] == '3.400000E+01'
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
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key)
    assert query.get_path() == "TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"


def test_update_entity_with_put_method_specified(service):
    """Make sure the method update_entity handles correctly when PUT method is specified"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key, method="PUT")
    assert query.get_method() == "PUT"


def test_update_entity_with_patch_method_specified(service):
    """Make sure the method update_entity handles correctly when PATCH method is specified"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key, method="PATCH")
    assert query.get_method() == "PATCH"

def test_update_entity_with_merge_method_specified(service):
    """Make sure the method update_entity handles correctly when MERGE method is specified"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key, method='merge')
    assert query.get_method() == 'MERGE'


def test_update_entity_with_no_method_specified(service):
    """Make sure the method update_entity handles correctly when no method is specified"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key)
    assert query.get_method() == "PATCH"


def test_update_entity_with_service_config_set_to_put(service):
    """Make sure the method update_entity handles correctly when no method is specified"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    service.config['http']['update_method'] = "PUT"
    query = service.entity_sets.TemperatureMeasurements.update_entity(key)
    assert query.get_method() == "PUT"


def test_update_entity_with_wrong_method_specified(service):
    """Make sure the method update_entity raises ValueError when wrong method is specified"""

    # pylint: disable=redefined-outer-name


    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    with pytest.raises(ValueError) as caught_ex:
        service.entity_sets.TemperatureMeasurements.update_entity(key, method='DELETE')

    assert str(caught_ex.value).startswith('The value "DELETE" is not on the list of allowed Entity Update HTTP Methods: PATCH, PUT, MERGE')


def test_get_entity_with_entity_key_and_other_params(service):
    """Make sure the method update_entity handles correctly the parameter key which is EntityKey"""

    # pylint: disable=redefined-outer-name

    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key=key, Foo='Bar')
    assert query.get_path() == "TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"


def test_get_entities_with_custom_headers(service):
    query = service.entity_sets.TemperatureMeasurements.get_entities()
    query.add_headers({"X-Foo": "bar"})

    assert query.get_headers() == {"Accept": "application/json", "X-Foo": "bar"}


def test_get_entity_with_custom_headers(service):
    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.get_entity(key)
    query.add_headers({"X-Foo": "bar"})

    assert query.get_headers() == {"Accept": "application/json", "X-Foo": "bar"}


def test_update_entities_with_custom_headers(service):
    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.update_entity(key)
    query.add_headers({"X-Foo": "bar"})

    assert query.get_headers() == {"Accept": "application/json", "Content-Type": "application/json", "X-Foo": "bar"}


def test_create_entity_with_custom_headers(service):
    query = service.entity_sets.TemperatureMeasurements.create_entity()
    query.add_headers({"X-Foo": "bar"})

    assert query.get_headers() == {"Accept": "application/json", "Content-Type": "application/json", "X-Requested-With": "X", "X-Foo": "bar"}


def test_create_entity_with_overwriting_custom_headers(service):
    query = service.entity_sets.TemperatureMeasurements.create_entity()
    query.add_headers({"X-Requested-With": "bar"})

    assert query.get_headers() == {"Accept": "application/json", "Content-Type": "application/json", "X-Requested-With": "bar"}


def test_create_entity_with_blank_custom_headers(service):
    query = service.entity_sets.TemperatureMeasurements.create_entity()
    query.add_headers({})

    assert query.get_headers() == {"Accept": "application/json", "Content-Type": "application/json", "X-Requested-With": "X"}


def test_pass_incorrect_header_type(service):
    query = service.entity_sets.TemperatureMeasurements.create_entity()

    with pytest.raises(TypeError) as ex:
        query.add_headers(69420)
        assert str(ex) == "TypeError: Headers must be of type 'dict' not <class 'int'>"


@responses.activate
def test_get_entities(service):
    """Get entities"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees",
        json={'d': {
            'results': [
                {
                    'ID': 669,
                    'NameFirst': 'Yennefer',
                    'NameLast': 'De Vengerberg'
                }
            ]
        }},
        status=200)

    request = service.entity_sets.Employees.get_entities()

    assert isinstance(request, pyodata.v2.service.QueryRequest)

    empls = request.execute()
    assert empls[0].ID == 669
    assert empls[0].NameFirst == 'Yennefer'
    assert empls[0].NameLast == 'De Vengerberg'


@responses.activate
def test_get_null_value_from_null_preserving_service(service_retain_null):
    """Get entity with missing property value as None type"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service_retain_null.url}/Employees",
        json={'d': {
            'results': [
                {
                    'ID': 1337,
                    'NameFirst': 'Neo',
                    'NameLast': None
                }
            ]
        }},
        status=200)

    request = service_retain_null.entity_sets.Employees.get_entities()

    the_ones = request.execute()
    assert the_ones[0].ID == 1337
    assert the_ones[0].NameFirst == 'Neo'
    assert the_ones[0].NameLast is None


@responses.activate
def test_get_null_value_from_non_null_preserving_service(service):
    """Get entity with missing property value as default type"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees",
        json={'d': {
            'results': [
                {
                    'ID': 1337,
                    'NameFirst': 'Neo',
                    'NameLast': None
                }
            ]
        }},
        status=200)

    request = service.entity_sets.Employees.get_entities()

    the_ones = request.execute()
    assert the_ones[0].ID == 1337
    assert the_ones[0].NameFirst == 'Neo'
    assert the_ones[0].NameLast == ''


@responses.activate
def test_get_non_nullable_value(service_retain_null):
    """Get error when receiving a null value for a non-nullable property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service_retain_null.url}/Employees",
        json={'d': {
            'results': [
                {
                    'ID': None,
                    'NameFirst': 'Neo',
                }
            ]
        }},
        status=200)

    with pytest.raises(PyODataException) as e_info:
        service_retain_null.entity_sets.Employees.get_entities().execute()

    assert str(e_info.value) == 'Value of non-nullable Property ID is null'


@responses.activate
def test_navigation_multi(service):
    """Get entities via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees(23)/Addresses",
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
        f"{service.url}/Employees(23)/Addresses(456)",
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
def test_navigation_multi_on1(service):
    """Check getting entity via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Customers('Mammon')/ReferredBy",
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'Name': 'John',
            }
        },
        status=200)

    request = service.entity_sets.Customers.get_entity('Mammon').nav('ReferredBy')
    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    referred_by_proxy = request.execute()
    assert isinstance(referred_by_proxy, pyodata.v2.service.NavEntityProxy)

    assert referred_by_proxy.entity_set._name == 'Customers'
    assert referred_by_proxy._entity_type.name == 'Customer'

    assert referred_by_proxy.Name == 'John'


@responses.activate
def test_navigation_1on1(service):
    """Check getting entity via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Cars('Hadraplan')/IDPic",
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
def test_navigation_1on1_from_entity_proxy(service):
    """Check getting entity via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Cars('Hadraplan')",
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'Name': 'Hadraplan',
            }
        },
        status=200)

    responses.add(
        responses.GET,
        f"{service.url}/Cars('Hadraplan')/IDPic",
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'CarName': 'Hadraplan',
            'Content': 'DEADBEAF',
            }
        },
        status=200)

    request = service.entity_sets.Cars.get_entity('Hadraplan')
    assert isinstance(request, pyodata.v2.service.EntityGetRequest)

    car_proxy = request.execute()
    assert isinstance(car_proxy, pyodata.v2.service.EntityProxy)

    assert car_proxy.Name == 'Hadraplan'

    idpic_proxy = car_proxy.nav('IDPic').execute()
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
        f"{service.url}/Cars('Hadraplan')/IDPic/$value/",
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
        f"{service.url}/Customers('Mammon')/Orders",
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
        f"{service.url}/Cars('Hadraplan')/IDPic",
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'CarName': 'Hadraplan',
            'Content': 'DEADBEAF',
            }
        },
        status=200)

    responses.add(
        responses.GET,
        f"{service.url}/Cars('Hadraplan')/IDPic/$value/",
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
        f"{service.url}/CarIDPics('Hadraplan')/$value/",
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
        f"{service.url}/CarIDPics('Hadraplan')",
        headers={'Content-type': 'application/json'},
        json = { 'd': {
            'CarName': 'Hadraplan',
            'Content': 'DEADBEAF',
            }
        },
        status=200)

    responses.add(
        responses.GET,
        f"{service.url}/CarIDPics('Hadraplan')/$value/",
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
        f"{service.url}/CarIDPics('Hadraplan')/$value/",
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
        f"{service.url}/Employees(23)/Addresses",
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
        f"{service.url}/Employees(23)",
        json={'d': {
            'ID': 23,
            'NameFirst': 'Rob',
            'NameLast': 'Ickes'
        }},
        status=200)

    responses.add(
        responses.GET,
        f"{service.url}/Employees(23)/Addresses",
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
        f"{service.url}/Employees(23)",
        json={'d': {
            'ID': 23,
            'NameFirst': 'Rob',
            'NameLast': 'Ickes'
        }},
        status=200)

    responses.add(
        responses.GET,
        f"{service.url}/Employees(23)/Addresses(456)",
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
        f"{service.url}/Employees(23)",
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
        f"{service.url}/Employees(23)",
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
                     b"{b'd': {'Sensor': 'Sensor-address', 'Date': datetime\'2017-12-24T18:00\', 'Value': '34.0d'}}"
                     b'\n'
                     b'--changeset_1--\n'
                     b'\n'
                     b'--batch_r1--')

    responses.add(
        responses.POST,
        f'{URL_ROOT}/$batch',
        body=response_body,
        content_type='multipart/mixed; boundary=batch_r1',
        status=202)

    batch = service.create_batch('batch1')

    chset = service.create_changeset('chset1')

    employee_request = service.entity_sets.Employees.get_entity(23)

    temp_request = service.entity_sets.TemperatureMeasurements.update_entity(
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc)).set(Value=34.0)

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
def test_enormous_batch_request(service):
    """Batch requests"""

    # pylint: disable=redefined-outer-name

    response_body = contents_of_fixtures_file('enormous_batch_response')

    responses.add(
        responses.POST,
        f'{URL_ROOT}/$batch',
        body=response_body,
        content_type='multipart/mixed; boundary=16804F9C063D8720EACA19F7DFB3CD4A0',
        status=202)

    batch = service.create_batch()

    employee_request = service.entity_sets.Enumerations.get_entities()

    batch.add_request(employee_request)

    response = batch.execute()

    assert len(response) == 1
    assert len(response[0]) == 1016


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
        f'{URL_ROOT}/$batch',
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
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

    query = service.entity_sets.TemperatureMeasurements.get_entity(key)
    assert query.get_path() == "TemperatureMeasurements(Sensor='sensor1',Date=datetime'2017-12-24T18:00:00')"


def test_get_entity_with_entity_key_and_other_params(service):
    """Make sure the method get_entity handles correctly the parameter key which is EntityKey"""

    # pylint: disable=redefined-outer-name

    key = EntityKey(
        service.schema.entity_type('TemperatureMeasurement'),
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc))

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


def test_get_entity_set_query_filter_lt(service):
    """Test the operator 'lt' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.Cars.get_entities()
    filter_str = request.Price < 2

    assert filter_str == "Price lt 2"


def test_get_entity_set_query_filter_le(service):
    """Test the operator 'le' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.Cars.get_entities()
    filter_str = request.Price <= 2

    assert filter_str == "Price le 2"


def test_get_entity_set_query_filter_ge(service):
    """Test the operator 'ge' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.Cars.get_entities()
    filter_str = request.Price >= 2

    assert filter_str == "Price ge 2"


def test_get_entity_set_query_filter_gt(service):
    """Test the operator 'gt' of $filter for humans"""

    # pylint: disable=redefined-outer-name, invalid-name

    request = service.entity_sets.Cars.get_entities()
    filter_str = request.Price > 2

    assert filter_str == "Price gt 2"


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

    with pytest.raises(KeyError) as e_info:
        assert not request.Foo == 'bar'
    assert e_info.value.args[0] == 'Foo'


@responses.activate
def test_inlinecount(service):
    """Check getting entities with $inlinecount"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees?$inlinecount=allpages",
        json={'d': {
            '__count': 3,
            'results': [
                {
                    'ID': 21,
                    'NameFirst': 'George',
                    'NameLast': 'Doe'
                },{
                    'ID': 22,
                    'NameFirst': 'John',
                    'NameLast': 'Doe'
                },{
                    'ID': 23,
                    'NameFirst': 'Rob',
                    'NameLast': 'Ickes'
                }
            ]
        }},
        status=200)

    request = service.entity_sets.Employees.get_entities().count(inline=True)

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute().total_count == 3


@responses.activate
def test_inlinecount_with_skip(service):
    """Check getting entities with $inlinecount with $skip"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees?$inlinecount=allpages&$skip=1",
        json={'d': {
            '__count': 3,
            'results': [
                {
                    'ID': 22,
                    'NameFirst': 'John',
                    'NameLast': 'Doe'
                },{
                    'ID': 23,
                    'NameFirst': 'Rob',
                    'NameLast': 'Ickes'
                }
            ]
        }},
        status=200)

    request = service.entity_sets.Employees.get_entities().skip(1).count(inline=True)

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute().total_count == 3


@responses.activate
def test_navigation_inlinecount(service):
    """Check getting entities with $inlinecount via navigation property"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees(23)/Addresses?$inlinecount=allpages",
        json={'d': {
            '__count': 3,
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
                    'City': 'Manchester'
                }
            ]
        }},
        status=200)

    addresses = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()
    request = addresses.count(inline=True)

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute().total_count == 3


@responses.activate
def test_inlinecount_with_filter(service):
    """Check getting entities with $inlinecount and $filter"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees(23)/Addresses?$inlinecount=allpages&%24filter=City%20eq%20%27London%27",
        json={'d': {
            '__count': 2,
            'results': [
                {
                    'ID': 456,
                    'Street': 'Baker Street',
                    'City': 'London'
                },{
                    'ID': 457,
                    'Street': 'Lowth Road',
                    'City': 'London'
                }
            ]
        }},
        status=200)

    addresses = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()
    request = addresses.filter(addresses.City == 'London').count(inline=True)

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute().total_count == 2


@responses.activate
def test_total_count_exception(service):
    """Check getting entities without $inlinecount and then requesting total_count"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees",
        json={'d': {
            'results': [
                {
                    'ID': 21,
                    'NameFirst': 'George',
                    'NameLast': 'Doe'
                },{
                    'ID': 22,
                    'NameFirst': 'John',
                    'NameLast': 'Doe'
                },{
                    'ID': 23,
                    'NameFirst': 'Rob',
                    'NameLast': 'Ickes'
                }
            ]
        }},
        status=200)

    request = service.entity_sets.Employees.get_entities()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    with pytest.raises(ProgramError) as e_info:
        request.execute().total_count

    assert str(e_info.value) == ('The collection does not include Total Count of items because '
                                 'the request was made without specifying "count(inline=True)".')


@responses.activate
def test_count(service):
    """Check getting $count"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count",
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
        f"{service.url}/Employees/$count?$skip=12",
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
        f"{service.url}/Employees(23)/Addresses/$count",
        json=458,
        status=200)

    addresses = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()
    request = addresses.count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 458


@responses.activate
def test_count_with_filter(service):
    """Check getting $count with $filter"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees(23)/Addresses/$count?%24filter=City%20eq%20%27London%27",
        json=3,
        status=200)

    addresses = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()
    request = addresses.filter(addresses.City == 'London').count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter(service):
    """Check getting $count with $filter and using new filter syntax"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees(23)/Addresses/$count?%24filter=City%20eq%20%27London%27",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entity(23).nav('Addresses').get_entities()
    request = employees.filter(City="London").count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_partial_listing(service):
    """Using __next URI to fetch all entities in a collection"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees?$inlinecount=allpages",
        json={'d': {
            '__count': 3,
            '__next': f"{service.url}/Employees?$inlinecount=allpages&$skiptoken='opaque'",
            'results': [
                {
                    'ID': 21,
                    'NameFirst': 'George',
                    'NameLast': 'Doe'
                },{
                    'ID': 22,
                    'NameFirst': 'John',
                    'NameLast': 'Doe'
                }
            ]
        }},
        status=200)

    responses.add(
        responses.GET,
        f"{service.url}/Employees?$inlinecount=allpages&$skiptoken='opaque'",
        json={'d': {
            '__count': 3,
            'results': [
                {
                    'ID': 23,
                    'NameFirst': 'Rob',
                    'NameLast': 'Ickes'
                }
            ]
        }},
        status=200)

    # Fetching (potentially) all entities, actually getting 2
    request = service.entity_sets.Employees.get_entities().count(inline=True)
    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)
    result = request.execute()
    assert len(result) == 2
    assert result.total_count == 3
    assert result.next_url is not None

    # Fetching next batch, receive the one remaining entity
    request = service.entity_sets.Employees.get_entities().next_url(result.next_url)
    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)
    result = request.execute()
    assert len(result) == 1
    assert result.total_count == 3, "(inline) count flag inherited from first request"
    assert result.next_url is None


@responses.activate
def test_count_with_chainable_filter_lt_operator(service):
    """Check getting $count with $filter with new filter syntax using multiple filters"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?%24filter=ID%20lt%2023",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__lt=23).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_lte_operator(service):
    """Check getting $count with $filter with new filter syntax using multiple filters"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?%24filter=ID%20le%2023",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__lte=23).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_gt_operator(service):
    """Check getting $count with $filter with new filter syntax using multiple filters"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?%24filter=ID%20gt%2023",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__gt=23).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_gte_operator(service):
    """Check getting $count with $filter with new filter syntax using multiple filters"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?%24filter=ID%20ge%2023",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__gte=23).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_eq_operator(service):
    """Check getting $count with $filter with new filter syntax using multiple filters"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?%24filter=ID%20eq%2023",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__eq=23).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_in_operator(service):
    """Check getting $count with $filter in"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=ID%20eq%201%20or%20ID%20eq%202%20or%20ID%20eq%203",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__in=[1,2,3]).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_startswith_operator(service):
    """Check getting $count with $filter in"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=startswith%28NickName%2C%20%27Tim%27%29%20eq%20true",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(NickName__startswith="Tim").count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_endswith_operator(service):
    """Check getting $count with $filter in"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=endswith%28NickName%2C%20%27othy%27%29%20eq%20true",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(NickName__endswith="othy").count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_length_operator(service):
    """Check getting $count with $filter in"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=length%28NickName%29%20eq%206",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(NickName__length=6).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_length_operator_as_string(service):
    """Check getting $count with $filter in"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=length%28NickName%29%20eq%206",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(NickName__length="6").count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_contains_operator(service):
    """Check getting $count with $filter in"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=substringof%28%27Tim%27%2C%20NickName%29%20eq%20true",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(NickName__contains="Tim").count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_range_operator(service):
    """Check getting $count with $filter in"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=ID%20gte%2020%20and%20ID%20lte%2050",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__range=(20, 50)).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_multiple(service):
    """Check getting $count with $filter with new filter syntax using multiple filters"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?%24filter=ID%20eq%2023%20and%20NickName%20eq%20%27Steve%27",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID=23, NickName="Steve").count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filter_or(service):
    """Check getting $count with $filter with FilterExpression syntax or"""
    from pyodata.v2.service import FilterExpression as Q
    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=%28ID%20eq%2023%20and%20NickName%20eq%20%27Steve%27%29%20or%20%28ID%20eq%2025%20and%20NickName%20eq%20%27Tim%27%29",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(Q(ID=23, NickName="Steve") | Q(ID=25, NickName="Tim")).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3

@responses.activate
def test_count_with_multiple_chainable_filters_startswith(service):
    """Check getting $count with $filter calling startswith"""
    from pyodata.v2.service import FilterExpression as Q
    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=%28ID%20eq%2023%20and%20startswith%28NickName%2C%20%27Ste%27%29%20eq%20true%29%20or%20%28ID%20eq%2025%20and%20NickName%20eq%20%27Tim%27%29",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(Q(ID=23, NickName__startswith="Ste") | Q(ID=25, NickName="Tim")).count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_count_with_chainable_filters_invalid_property_lookup(service):
    """Check getting $count with $filter calling startswith"""
    # pylint: disable=redefined-outer-name

    employees = service.entity_sets.Employees.get_entities()
    with pytest.raises(ValueError) as ex:
        request = employees.filter(Foo="Bar")

    assert str(ex.value) == '"Foo" is not a valid property or operator'


@responses.activate
def test_count_with_chainable_filters_invalid_operator_lookup(service):
    """Check getting $count with $filter calling startswith"""
    # pylint: disable=redefined-outer-name

    employees = service.entity_sets.Employees.get_entities()
    with pytest.raises(ValueError) as ex:
        request = employees.filter(NickName__foo="Bar")

    assert str(ex.value) == '"foo" is not a valid property or operator'


@responses.activate
def test_count_with_chained_filters(service):
    """Check getting $count with chained filters"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?$filter=ID%20gte%2020%20and%20ID%20lte%2050%20and%20NickName%20eq%20%27Tim%27",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities()
    request = employees.filter(ID__range=(20, 50)).filter(NickName="Tim").count()

    assert isinstance(request, pyodata.v2.service.GetEntitySetRequest)

    assert request.execute() == 3


@responses.activate
def test_create_entity_with_utc_datetime(service):
    """Basic test on creating entity with an UTC datetime object"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        f"{service.url}/TemperatureMeasurements",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'Sensor1',
            'Date': '/Date(1514138400000)/',
            'Value': '34.0d'
        }},
        status=201)

    request = service.entity_sets.TemperatureMeasurements.create_entity().set(**{
        'Sensor': 'Sensor1',
        'Date': datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc),
        'Value': 34.0
    })

    assert request._values['Date'] == '/Date(1514138400000)/'

    result = request.execute()
    assert result.Date == datetime.datetime(2017, 12, 24, 18, 0, tzinfo=datetime.timezone.utc)


@responses.activate
def test_create_entity_with_non_utc_datetime(service):
    """
        Basic test on creating entity with an non-UTC datetime object
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
        f"{service.url}/TemperatureMeasurements",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'Sensor1',
            'Date': '/Date(1514138400000)/',
            'Value': '34.0d'
        }},
        status=201)

    with pytest.raises(PyODataModelError) as e_info:
        # Offset -18000 sec is for America/Chicago (CDT) timezone
        service.entity_sets.TemperatureMeasurements.create_entity().set(**{
            'Sensor': 'Sensor1',
            'Date': datetime.datetime(2017, 12, 24, 18, 0, tzinfo=MyUTCOffsetTimezone(-18000)),
            'Value': 34.0
        })


@responses.activate
def test_create_entity_with_naive_datetime(service):
    """Preventing creation/usage of an entity with an unaware datetime object"""

    with pytest.raises(PyODataModelError) as e_info:
        service.entity_sets.TemperatureMeasurements.create_entity().set(**{
            'Sensor': 'Sensor1',
            'Date': datetime.datetime(2017, 12, 24, 18, 0),
            'Value': 34.0
        })
    assert str(e_info.value).startswith('Edm.DateTime accepts only UTC')


@responses.activate
def test_null_datetime(service):
    """Test default value of DateTime. Default value gets inserted when a property is null"""

    responses.add(
        responses.GET,
        f"{service.url}/TemperatureMeasurements",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'results': [
                {
                    'Date': None,
                }
            ]
        }},
        status=200)

    result = service.entity_sets.TemperatureMeasurements.get_entities().execute()

    assert result[0].Date == datetime.datetime(1753, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)


@responses.activate
def test_parsing_of_datetime_before_unix_time(service):
    """Test DateTime handling of time before 1970"""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.POST,
        f"{service.url}/TemperatureMeasurements",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'Sensor': 'Sensor1',
            'Date': '/Date(-777877200000)/',
            'Value': '34.0d'
        }},
        status=201)

    request = service.entity_sets.TemperatureMeasurements.create_entity().set(**{
        'Sensor': 'Sensor1',
        'Date': datetime.datetime(1945, 5, 8, 19, 0, tzinfo=datetime.timezone.utc),
        'Value': 34.0
    })

    assert request._values['Date'] == '/Date(-777877200000)/'

    result = request.execute()
    assert result.Date == datetime.datetime(1945, 5, 8, 19, 0, tzinfo=datetime.timezone.utc)


@responses.activate
@pytest.mark.parametrize("json_input,expected", [
    ('/Date(981173106000+0001)/', datetime.datetime(2001, 2, 3, 4, 5, 6,
                                                    tzinfo=datetime.timezone(datetime.timedelta(minutes=1)))),
    ('/Date(981173106000-0001)/', datetime.datetime(2001, 2, 3, 4, 5, 6,
                                                    tzinfo=datetime.timezone(-datetime.timedelta(minutes=1)))),
    (None, datetime.datetime(1753, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)),
])
def test_parsing_of_datetimeoffset(service, json_input, expected):
    """Test DateTimeOffset handling."""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/TemperatureMeasurements",
        headers={'Content-type': 'application/json'},
        json={'d': {
            'results': [
                {
                    'Sensor': 'Sensor1',
                    'Date': '/Date(-981173106000)/',
                    'DateTimeWithOffset': json_input,
                    'Value': '34.0d'
                }
            ]
        }},
        status=200)

    result = service.entity_sets.TemperatureMeasurements.get_entities().execute()

    assert result[0].DateTimeWithOffset == expected


@responses.activate
def test_mismatched_etags_in_body_and_header(service):
    """Test creating entity with missmatched etags"""

    responses.add(
        responses.POST,
        f"{service.url}/MasterEntities",
        headers={
            'Content-type': 'application/json',
            'ETag':  'W/\"JEF\"'
        },
        json={'d': {
            '__metadata': {
                'etag': 'W/\"PEF\"',
            }
        }},
        status=201)

    with pytest.raises(PyODataException) as e_info:
        service.entity_sets.MasterEntities.create_entity().set(**{}).execute()

    assert str(e_info.value) == 'Etag from header does not match the Etag from response body'


def test_odata_http_response():
    """Test that ODataHttpResponse is complaint with requests.Reponse"""

    response_string = 'HTTP/1.1 200 OK \n' \
                      'Content-Type: application/json\n' \
                      '\n' \
                      '{"d": {"ID": 23 }}'

    response = ODataHttpResponse.from_string(response_string)

    assert response.status_code == HTTP_CODE_OK

    assert isinstance(response.headers, dict)
    assert response.headers['Content-Type'] == 'application/json'
    assert response.json()['d']['ID'] == 23


@responses.activate
def test_custom_with_get_entity(service):
    """ Test that `custom` can be called after `get_entity`"""

    responses.add(
        responses.GET,
        f"{service.url}/MasterEntities('12345')?foo=bar",
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    entity = service.entity_sets.MasterEntities.get_entity('12345').custom("foo", "bar").execute()
    assert entity.Key == '12345'

@responses.activate
def test_custom_with_get_entity_url_params(service):
    """ Test that `custom` after `get_entity` is setting up correctly URL parts """

    responses.add(
        responses.GET,
        f"{service.url}/MasterEntities('12345')?foo=bar",
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    oDataHttpRequest = service.entity_sets.MasterEntities.get_entity('12345').custom("foo", "bar")
    assert oDataHttpRequest.get_query_params() == {'foo': 'bar'}
    assert oDataHttpRequest.get_path() == "MasterEntities('12345')"

    entity = oDataHttpRequest.execute()
    assert entity.Key == '12345'

@responses.activate
def test_multiple_custom_with_get_entity_url_params(service):
    """ Test that `custom` after `get_entity` called several times is setting up correctly URL parts """

    responses.add(
        responses.GET,
        f"{service.url}/MasterEntities('12345')?foo=bar&$fizz=buzz",
        headers={'Content-type': 'application/json'},
        json={'d': {'Key': '12345'}},
        status=200)

    oDataHttpRequest = service.entity_sets.MasterEntities.get_entity('12345').custom("foo", "bar").custom("$fizz", "buzz")
    assert oDataHttpRequest.get_query_params() == {'foo': 'bar', '$fizz': 'buzz'}
    assert oDataHttpRequest.get_path() == "MasterEntities('12345')"

    entity = oDataHttpRequest.execute()
    assert entity.Key == '12345'


@responses.activate
def test_custom_with_get_entities_and_chained_filters_url_params(service):
    """ Test that `custom` after `get_entities` works with complex query (count, filter) """
    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service.url}/Employees/$count?foo=bar&$fizz=buzz&$filter=ID%20gte%2020%20and%20ID%20lte%2050%20and%20NickName%20eq%20%27Tim%27",
        json=3,
        status=200)

    employees = service.entity_sets.Employees.get_entities().custom("foo", "bar").custom("$fizz", "buzz")
    request = employees.filter(ID__range=(20, 50)).filter(NickName="Tim").count()

    assert request.get_query_params() == {'foo': 'bar', '$fizz': 'buzz', '$filter': "ID gte 20 and ID lte 50 and NickName eq 'Tim'"}
    assert request.get_path() == 'Employees/$count'


@responses.activate
def test_custom_with_create_entity_url_params(service):
    """Test that `custom` after creating entity works correctly"""

    # pylint: dispyable=redefined-outer-name

    responses.add(
        responses.POST,
        f"{service.url}/MasterEntities?foo=bar",
        headers={
            'Content-type': 'application/json',
            'ETag':  'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"'
        },
        json={'d': {
            '__metadata': {
                'etag': 'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"',
            },
            'Key': '12345',
            'Data': 'abcd'
        }},
        status=201)

    oDataHttpRequest = service.entity_sets.MasterEntities.create_entity().set(**{'Key': '1234', 'Data': 'abcd'}).custom("foo", "bar")

    assert oDataHttpRequest.get_query_params() == {'foo': 'bar'}
    assert oDataHttpRequest.get_path() == 'MasterEntities'
    assert oDataHttpRequest.get_method() == 'POST'
    assert oDataHttpRequest.get_body() == '{"Key": "1234", "Data": "abcd"}'

    result = oDataHttpRequest.execute()

    assert result.Key == '12345'
    assert result.Data == 'abcd'
    assert result.etag == 'W/\"J0FtZXJpY2FuIEFpcmxpbmVzJw==\"'