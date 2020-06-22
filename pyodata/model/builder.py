"""Metadata Builder Implementation"""

import io
from typing import TypeVar, Dict

from lxml import etree

from pyodata.config import Config
from pyodata.exceptions import PyODataParserError
from pyodata.model.elements import ValueHelperParameter, Schema, build_element
from pyodata.type_declarations import ETreeType

XMLType = TypeVar('XMLType', str, bytes)
AliasesType = Dict[str, str]

ANNOTATION_NAMESPACES = {
    'edm': 'http://docs.oasis-open.org/odata/ns/edm',
    'edmx': 'http://docs.oasis-open.org/odata/ns/edmx'
}

SAP_VALUE_HELPER_DIRECTIONS = {
    'com.sap.vocabularies.Common.v1.ValueListParameterIn': ValueHelperParameter.Direction.In,
    'com.sap.vocabularies.Common.v1.ValueListParameterInOut': ValueHelperParameter.Direction.InOut,
    'com.sap.vocabularies.Common.v1.ValueListParameterOut': ValueHelperParameter.Direction.Out,
    'com.sap.vocabularies.Common.v1.ValueListParameterDisplayOnly': ValueHelperParameter.Direction.DisplayOnly,
    'com.sap.vocabularies.Common.v1.ValueListParameterFilterOnly': ValueHelperParameter.Direction.FilterOnly
}


# pylint: disable=protected-access
class MetadataBuilder:
    """Metadata builder"""

    EDMX_WHITELIST = [
        'http://schemas.microsoft.com/ado/2007/06/edmx',
        'http://docs.oasis-open.org/odata/ns/edmx',
    ]

    EDM_WHITELIST = [
        'http://schemas.microsoft.com/ado/2006/04/edm',
        'http://schemas.microsoft.com/ado/2007/05/edm',
        'http://schemas.microsoft.com/ado/2008/09/edm',
        'http://schemas.microsoft.com/ado/2009/11/edm',
        'http://docs.oasis-open.org/odata/ns/edm'
    ]

    def __init__(self, xml: XMLType, config: Config):
        self._xml = xml
        self._config = config

    # pylint: disable=missing-docstring
    @property
    def config(self) -> Config:
        return self._config

    def build(self):
        """ Build model from the XML metadata"""

        if isinstance(self._xml, str):
            mdf = io.StringIO(self._xml)
        elif isinstance(self._xml, bytes):
            mdf = io.BytesIO(self._xml)
        else:
            raise TypeError('Expected bytes or str type on metadata_xml, got : {0}'.format(type(self._xml)))

        namespaces = self._config.namespaces
        xml = etree.parse(mdf)
        edmx = xml.getroot()

        try:
            dataservices = next((child for child in edmx if etree.QName(child.tag).localname == 'DataServices'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element DataServices')

        try:
            schema = next((child for child in dataservices if etree.QName(child.tag).localname == 'Schema'))
        except StopIteration:
            raise PyODataParserError('Metadata document is missing the element Schema')

        if 'edmx' not in self._config.namespaces:
            namespace = etree.QName(edmx.tag).namespace

            if namespace not in self.EDMX_WHITELIST:
                raise PyODataParserError(f'Unsupported Edmx namespace - {namespace}')

            namespaces['edmx'] = namespace

        if 'edm' not in self._config.namespaces:
            namespace = etree.QName(schema.tag).namespace

            if namespace not in self.EDM_WHITELIST:
                raise PyODataParserError(f'Unsupported Schema namespace - {namespace}')

            namespaces['edm'] = namespace

        self._config.namespaces = namespaces

        self._config._sap_value_helper_directions = SAP_VALUE_HELPER_DIRECTIONS
        self._config._annotation_namespaces = ANNOTATION_NAMESPACES

        self.update_alias(self.get_aliases(xml, self._config), self._config)

        edm_schemas = xml.xpath('/edmx:Edmx/edmx:DataServices/edm:Schema', namespaces=self._config.namespaces)
        return build_element(Schema, self._config, schema_nodes=edm_schemas)

    @staticmethod
    def get_aliases(edmx: ETreeType, config: Config):
        """Get all aliases"""

        # aliases = collections.defaultdict(set)
        aliases = {}
        edm_root = edmx.xpath('/edmx:Edmx', namespaces=config.namespaces)
        if edm_root:
            edm_ref_includes = edm_root[0].xpath('edmx:Reference/edmx:Include', namespaces=config.annotation_namespace)
            for ref_incl in edm_ref_includes:
                namespace = ref_incl.get('Namespace')
                alias = ref_incl.get('Alias')
                if namespace is not None and alias is not None:
                    aliases[alias] = namespace
                    # aliases[namespace].add(alias)

        return aliases

    @staticmethod
    def update_alias(aliases: AliasesType, config: Config):
        """Update config with aliases"""
        config.aliases = aliases
        helper_direction_keys = list(config.sap_value_helper_directions.keys())

        for direction_key in helper_direction_keys:
            namespace, suffix = direction_key.rsplit('.', 1)
            for alias, alias_namespace in aliases.items():
                if alias_namespace == namespace:
                    config._sap_value_helper_directions[alias + '.' + suffix] = \
                        config.sap_value_helper_directions[direction_key]
