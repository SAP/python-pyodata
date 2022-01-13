"""PyOData Vendor SAP tests"""

import logging
from typing import NamedTuple, ByteString
import pytest
from pyodata.exceptions import PyODataException, HttpError
from pyodata.vendor import SAP
import responses
import requests
import json


class MockResponse(NamedTuple):
    content: ByteString


@pytest.fixture
def response_with_error():
    return MockResponse(
        b'{"error": { "message": { "value": "Gateway Error" } } }')

@pytest.fixture
def response_with_error_and_innererror():
    return MockResponse(
        b'{ "error": {\n\
              "message": { "value": "Gateway Error" },\n\
              "innererror": { "errordetails" : [\n\
                             { "message" : "Inner Error 1" },\n\
                             { "message" : "Inner Error 2" } ] } } }\n')


def test_parse_invalid_json():
    """Make sure an invalid JSON does not cause a disaster"""

    sap_error = SAP.BusinessGatewayError('Programmer message',
                                         MockResponse(b'random data'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_without_error():
    """Make sure a JSON without error member does not cause a disaster"""

    sap_error = SAP.BusinessGatewayError('Programmer message',
                                         MockResponse(b'{"random": "data"}'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_without_error_object():
    """Make sure a JSON without error member does not cause a disaster"""

    sap_error = SAP.BusinessGatewayError('Programmer message',
                                         MockResponse(b'{"error": "data"}'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_without_message():
    """Make sure a JSON without message member does not cause a disaster"""

    sap_error = SAP.BusinessGatewayError('Programmer message',
                                         MockResponse(b'{"error": { "data" : "foo" } }'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_without_message_object():
    """Make sure a JSON without message member does not cause a disaster"""

    sap_error = SAP.BusinessGatewayError('Programmer message',
                                         MockResponse(b'{"error": { "message" : "foo" } }'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_without_value():
    """Make sure a JSON without value member does not cause a disaster"""

    sap_error = SAP.BusinessGatewayError(
        'Programmer message',
        MockResponse(b'{"error": { "message" : { "foo" : "value" } } }'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_with_error(response_with_error):
    """Make sure a JSON without message member does not cause a disaster"""

    sap_error = SAP.BusinessGatewayError(
        'Programmer message',
        response_with_error)

    assert str(sap_error) == 'Gateway Error'
    assert not sap_error.errordetails


def test_parse_without_errordetails():
    """Make sure a JSON without errordetails member
       does not cause a disaster
    """

    sap_error = SAP.BusinessGatewayError(
        'Programmer message',
        MockResponse(b'{"error" : {\n\
            "innererror": { "message" : "value" } } }'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_without_array_errordetails():
    """Make sure a JSON without array errordetails member
       does not cause a disaster
    """

    sap_error = SAP.BusinessGatewayError(
        'Programmer message',
        MockResponse(b'{"error" : {\n\
            "innererror": { "errordetails" : "value" } } }'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_errordetails_no_object():
    """Make sure a JSON where error details are not objects
       does not cause a disaster
    """

    sap_error = SAP.BusinessGatewayError(
        'Programmer message',
        MockResponse(b'{"error" : {\n\
            "innererror": { "errordetails" : [ "foo", "bar" ] } } }'))

    assert str(sap_error) == 'Programmer message'
    assert not sap_error.errordetails


def test_parse_errordetails_no_message():
    """Make sure a JSON where error details misses the member message
       does not cause a disaster
    """

    sap_error = SAP.BusinessGatewayError(
        'Programmer message',
        MockResponse(b'{"error" : {\n\
            "innererror": { "errordetails" : [ { "foo" : "bar" } ] } } }'))

    assert str(sap_error) == 'Programmer message'
    assert [''] == sap_error.errordetails


def test_parse_with_error_and_innererror(response_with_error_and_innererror):
    """Make sure we parse out data correctly"""

    sap_error = SAP.BusinessGatewayError(
        'Programmer error',
        response_with_error_and_innererror)

    assert str(sap_error) == 'Gateway Error'
    assert sap_error.errordetails
    assert 2 == len(sap_error.errordetails)
    assert sap_error.errordetails[0] == 'Inner Error 1'
    assert sap_error.errordetails[1] == 'Inner Error 2'


def test_vendor_http_error(response_with_error):
    """Check that HttpError correctly returns
       an instance of BusinessGatewayError
    """

    logging.debug('First run')
    http_error = HttpError('Foo bar', response_with_error)
    assert isinstance(http_error, HttpError)
    assert str(http_error) == 'Foo bar'

    logging.debug('Second run')
    HttpError.VendorType = SAP.BusinessGatewayError
    sap_error = HttpError('Another foo bar', response_with_error)
    assert isinstance(sap_error, SAP.BusinessGatewayError)
    assert str(sap_error) == 'Gateway Error'


MOCK_AUTH_URL = "https://example.authentication.hana.ondemand.com"
MOCK_BTP_USER = "example_btp_user@gmail.com"
MOCK_BTP_PASSWORD = "example_password"
MOCK_KEY = {
    "uaa": {
        "url": MOCK_AUTH_URL,
        "clientid": "example-client-id",
        "clientsecret": "example-client-secret"
    }
}


@responses.activate
def test_add_btp_token_to_session_valid():
    """Valid username, password and key return a session with set token"""

    responses.add(
        responses.POST,
        MOCK_AUTH_URL + f'/oauth/token?grant_type=password&username={MOCK_BTP_USER}&password={MOCK_BTP_PASSWORD}',
        headers={'Content-type': 'application/json'},
        json={
            'access_token': 'valid_access_token',
            'token_type': 'bearer',
            'id_token': 'valid_id_token',
            'refresh_token': 'valid_refresh_token',
            'expires_in': 43199,
            'scope': 'openid uaa.user',
            'jti': 'valid_jti'
        },
        status=200)

    result = SAP.add_btp_token_to_session(requests.Session(), MOCK_KEY, MOCK_BTP_USER, MOCK_BTP_PASSWORD)
    assert result.headers['Authorization'] == 'Bearer valid_id_token'


@responses.activate
def test_add_btp_token_to_session_invalid_user():
    """Invalid username returns an HttpError"""

    invalid_user = "invalid@user.com"

    responses.add(
        responses.POST,
        MOCK_AUTH_URL + f'/oauth/token?grant_type=password&username={invalid_user}&password={MOCK_BTP_PASSWORD}',
        headers={'Content-type': 'application/json'},
        json={
            'error': 'unauthorized',
            'error_description': {
                'error': 'invalid_grant',
                'error_description': 'User authentication failed.'
            }
        },
        status=401)

    with pytest.raises(HttpError) as caught:
        SAP.add_btp_token_to_session(requests.Session(), MOCK_KEY, invalid_user, MOCK_BTP_PASSWORD)

    assert caught.value.response.status_code == 401
    assert json.loads(caught.value.response.text)['error_description']['error'] == 'invalid_grant'


@responses.activate
def test_add_btp_token_to_session_invalid_clientid():
    """Invalid clientid in key returns an HttpError"""

    invalid_key = MOCK_KEY.copy()
    invalid_key['uaa']['clientid'] = 'invalid-client-id'

    responses.add(
        responses.POST,
        MOCK_AUTH_URL + f'/oauth/token?grant_type=password&username={MOCK_BTP_USER}&password={MOCK_BTP_PASSWORD}',
        headers={'Content-type': 'application/json'},
        json={
            'error': 'unauthorized',
            'error_description': 'Bad credentials'
        },
        status=401)

    with pytest.raises(HttpError) as caught:
        SAP.add_btp_token_to_session(requests.Session(), invalid_key, MOCK_BTP_USER, MOCK_BTP_PASSWORD)

    assert caught.value.response.status_code == 401
    assert json.loads(caught.value.response.text)['error_description'] == 'Bad credentials'
