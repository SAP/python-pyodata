"""PyTest Fixtures"""
import os
from typing import Type
import pytest
import jinja2

from pyodata.config import Config
from pyodata.version import ODATAVersion
from pyodata.model.builder import MetadataBuilder
from pyodata.v4 import ODataV4
from pyodata.v2 import ODataV2


def _path_to_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, file_name)


@pytest.fixture
def template_builder():
    def _builder(version: Type[ODATAVersion], **kwargs):
        if version == ODataV4:
            config = Config(ODataV4)
            template = 'v4/metadata.template.xml'
        else:
            config = Config(ODataV2)
            template = 'v4/metadata.template.xml'

        with open(_path_to_file(template), 'rb') as metadata_file:
            template = jinja2.Template(metadata_file.read().decode("utf-8"))
            template = template.render(**kwargs).encode('ascii')

        return MetadataBuilder(template, config=config), config

    return _builder