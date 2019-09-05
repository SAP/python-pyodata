from typing import List
import pytest

from pyodata.config import Config, ODATAVersion
from pyodata.exceptions import PyODataParserError
from pyodata.model.builder import MetadataBuilder
from pyodata.model.elements import Schema, Types


def test_from_etree_mixin(metadata):
    """Test FromEtreeMixin class"""

    class EmptyODATA(ODATAVersion):
        @staticmethod
        def from_etree_callbacks():
            return {}

    config = Config(EmptyODATA)
    builder = MetadataBuilder(metadata, config=config)

    with pytest.raises(PyODataParserError) as typ_ex_info:
        builder.build()

    assert typ_ex_info.value.args[0] == f'{Schema.__name__} is unsupported in {config.odata_version.__name__}'


def test_supported_primitive_types():
    """Test handling of unsupported primitive types class"""

    class EmptyODATA(ODATAVersion):
        @staticmethod
        def supported_primitive_types() -> List[str]:
            return [
                'Edm.Binary'
            ]

    config = Config(EmptyODATA)
    with pytest.raises(KeyError) as typ_ex_info:
        Types.from_name('UnsupportedType', config)

    assert typ_ex_info.value.args[0] == f'Requested primitive type is not supported in this version of ODATA'

    assert Types.from_name('Edm.Binary', config).name == 'Edm.Binary'


def test_odata_version_statelessness():

    class EmptyODATA(ODATAVersion):
        @staticmethod
        def from_etree_callbacks():
            return {}

        @staticmethod
        def supported_primitive_types() -> List[str]:
            return []

    with pytest.raises(RuntimeError) as typ_ex_info:
        EmptyODATA()

    assert typ_ex_info.value.args[0] == 'ODATAVersion and its children are intentionally stateless, ' \
                                        'therefore you can not create instance of them'
