"""Service tests"""

import datetime
import responses
import requests
import pytest
import pyodata.v2.model
import pyodata.v2.service
from pyodata.exceptions import PyODataException, HttpError
from pyodata.v2.service import EntityKey

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
    assert entity.Date == datetime.datetime(2017, 12, 24, 18, 0)


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
        "{0}/sum?A=2&B=4'".format(service.url),
        headers={'Content-type': 'application/json'},
        json={'d': 6},
        status=200)

    result = service.functions.sum.parameter('A', 2).parameter('B', 4).execute()
    assert result == 6


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
            'Date': "datetime'2017-12-24T18:00'",
            'Value': 34
        }},
        status=204)

    request = service.entity_sets.TemperatureMeasurements.update_entity(
        Sensor='sensor1',
        Date=datetime.datetime(2017, 12, 24, 18, 0))

    assert isinstance(request, pyodata.v2.service.EntityModifyRequest)

    request.set(Value=34)

    request.execute()


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

    response_body = ('--batch_r1\n'
                     'Content-Type: application/http\n'
                     'Content-Transfer-Encoding: binary\n'
                     '\n'
                     'HTTP/1.1 200 OK\n'
                     'Content-Type: application/json\n'
                     '\n'
                     '{"d": {"ID": 23, "NameFirst": "Rob", "NameLast": "Ickes", "Address": { "ID": 456, "Street": "Baker Street", "City": "London"} }}'
                     '\n'
                     '--batch_r1\n'
                     'Content-Type: multipart/mixed; boundary=changeset_1\n'
                     '\n'
                     '--changeset_1\n'
                     'Content-Type: application/http\n'
                     'Content-Transfer-Encoding: binary\n'
                     '\n'
                     'HTTP/1.1 204 Updated\n'
                     'Content-Type: application/json\n'
                     '\n'
                     "{'d': {'Sensor': 'Sensor-address', 'Date': datetime\'2017-12-24T18:00\', 'Value': 34}}"
                     '\n'
                     '--changeset_1--\n'
                     '\n'
                     '--batch_r1--')

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
