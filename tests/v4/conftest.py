"""PyTest Fixtures"""
import pytest

from pyodata.config import Config
from pyodata.model.builder import MetadataBuilder
from pyodata.v4 import ODataV4, Schema
from tests.conftest import _path_to_file


@pytest.fixture
def inline_namespaces():
    return 'xmlns="MyEdm" xmlns:edmx="MyEdmx"'


@pytest.fixture
def config():
    return Config(ODataV4, xml_namespaces={
        'edmx': 'MyEdmx',
        'edm': 'MyEdm'
    })


@pytest.fixture
def metadata():
    with open(_path_to_file('v4/metadata.xml'), 'rb') as metadata:
        return metadata.read()


@pytest.fixture
def schema(metadata) -> Schema:
    meta = MetadataBuilder(
        metadata,
        config=Config(ODataV4)
    )

    return meta.build()
