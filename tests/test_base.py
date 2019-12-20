from typing import List
import pytest

from pyodata.config import Config
from pyodata.version import ODATAVersion
from pyodata.exceptions import PyODataParserError, PyODataModelError
from pyodata.model.builder import MetadataBuilder
from pyodata.model.elements import Schema, Types, Typ, build_element
from pyodata.v2 import ODataV2


def test_build_element():
    """Test FromEtreeMixin class"""

    class EmptyODATA(ODATAVersion):
        @staticmethod
        def build_functions():
            return {}

    config = Config(EmptyODATA)

    class TestElement:
        pass

    with pytest.raises(PyODataParserError) as typ_ex_info:
        build_element(TestElement, config)

    assert typ_ex_info.value.args[0] == f'{TestElement.__name__} is unsupported in {config.odata_version.__name__}'


def test_supported_primitive_types():
    """Test handling of unsupported primitive types class"""

    class EmptyODATA(ODATAVersion):
        @staticmethod
        def primitive_types() -> List[Typ]:
            return [
                Typ('Edm.Binary', 'binary\'\'')
            ]

    config = Config(EmptyODATA)
    with pytest.raises(PyODataModelError) as typ_ex_info:
        Types.from_name('UnsupportedType', config)

    assert typ_ex_info.value.args[0] == f'Requested primitive type UnsupportedType ' \
                                        f'is not supported in this version of ODATA'

    assert Types.from_name('Edm.Binary', config).name == 'Edm.Binary'


def test_odata_version_statelessness():

    class EmptyODATA(ODATAVersion):
        @staticmethod
        def build_functions():
            return {}

        @staticmethod
        def primitive_types() -> List[Typ]:
            return []

        @staticmethod
        def annotations():
            pass

    with pytest.raises(RuntimeError) as typ_ex_info:
        EmptyODATA()

    assert typ_ex_info.value.args[0] == 'ODATAVersion and its children are intentionally stateless, ' \
                                        'therefore you can not create instance of them'


def test_types_repository_separation():
    ODataV2.Types = dict()

    class TestODATA(ODATAVersion):
        @staticmethod
        def primitive_types() -> List['Typ']:
            return [
                Typ('PrimitiveType', '0')
            ]

    config_test = Config(TestODATA)
    config_v2 = Config(ODataV2)

    assert not TestODATA.Types
    assert TestODATA.Types == ODataV2.Types

    # Build type repository by initial call
    Types.from_name('PrimitiveType', config_test)
    Types.from_name('Edm.Int16', config_v2)

    assert ODataV2.Types
    assert TestODATA.Types != ODataV2.Types