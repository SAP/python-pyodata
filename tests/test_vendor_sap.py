"""PyOData Vendor SAP tests"""

import logging
from typing import NamedTuple, ByteString
import pytest
from pyodata.exceptions import PyODataException, HttpError
from pyodata.vendor import SAP


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
