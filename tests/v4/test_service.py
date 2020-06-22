import logging

import logging

# logging.basicConfig()
#
# root_logger = logging.getLogger()
# root_logger.setLevel(logging.DEBUG)

import pytest
import requests

from pyodata.model.elements import Types
from pyodata.exceptions import PyODataException
from pyodata.client import Client
from pyodata.config import Config
from pyodata.v4 import ODataV4

URL_ROOT = 'http://localhost:8888/odata/4/Default.scv/'


@pytest.fixture
def service():
    """Service fixture"""
    # metadata = _fetch_metadata(requests.Session(), URL_ROOT)
    # config = Config(ODataV4)
    # schema = MetadataBuilder(metadata, config=config).build()
    #
    # return Service(URL_ROOT, schema, requests.Session())

    # typ = Types.from_name('Collection(Edm.Int32)', Config(ODataV4))
    # t = typ.traits.from_json(['23', '34'])
    # assert typ.traits.from_json(['23', '34']) == [23, 34]

    return Client(URL_ROOT, requests.Session(), config=Config(ODataV4))


@pytest.fixture
def airport_entity():
    return {
        'Name': 'Dawn Summit 2',
        'Location': {
            'Address': 'Gloria',
            'City': 'West'
        }}


# def test_create_entity(service, airport_entity):
#     """Basic test on creating entity"""
#
#     result = service.entity_sets.Airports.create_entity().set(**airport_entity).execute()
#     assert result.Name == 'Dawn Summit 2'
#     assert result.Location['Address'] == 'Gloria'
#     assert result.Location['City'] == 'West'
#     assert isinstance(result.Id, int)
#
#
# def test_create_entity_code_400(service, airport_entity):
#     """Test that exception is raised in case of incorrect return code"""
#
#     del airport_entity['Name']
#     with pytest.raises(PyODataException) as e_info:
#         service.entity_sets.Airports.create_entity().set(**airport_entity).execute()
#
#     assert str(e_info.value).startswith('HTTP POST for Entity Set')
#
#
# def test_create_entity_nested(service):
#     """Basic test on creating entity"""
#
#     # pylint: disable=redefined-outer-name
#
#     entity = {
#         'Emails': [
#             'christopher32@hotmail.com',
#             'danielwarner@wallace.biz'
#         ],
#         'AddressInfo': [{
#             'Address': '8561 Ruth Course\\nTonyton, MA 75643',
#             'City': 'North Kristenport'
#         }],
#         'Gender': 'Male',
#         'UserName': 'Kenneth Allen',
#         'Pictures': [{
#             'Name': 'wish.jpg'
#         }]
#     }
#
#     result = service.entity_sets.Persons.create_entity().set(**entity).execute()
#
#     pass
    # assert result.Name == 'Hadraplan'
    # assert result.nav('IDPic').get_value().execute().content == b'DEADBEEF'
