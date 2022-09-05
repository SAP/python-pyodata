"""PyTest Fixtures"""
import logging
import os

import pytest

from pyodata.v2.model import schema_from_xml, Types


def contents_of_fixtures_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    path_to_file = os.path.join(current_directory, file_name)

    with open(path_to_file, 'rb') as md_file:
        return md_file.read()


@pytest.fixture
def metadata():
    """Example OData metadata"""
    return contents_of_fixtures_file("metadata.xml")


@pytest.fixture
def xml_builder_factory():
    """Skeleton OData metadata"""

    class XMLBuilder:
        """Helper class for building XML metadata document"""

        # pylint: disable=too-many-instance-attributes,line-too-long
        def __init__(self):
            self.reference_is_enabled = True
            self.data_services_is_enabled = True
            self.schema_is_enabled = True

            self.namespaces = {
                'edmx': "http://schemas.microsoft.com/ado/2007/06/edmx",
                'sap': 'http://www.sap.com/Protocols/SAPData',
                'edm': 'http://schemas.microsoft.com/ado/2008/09/edm',
                'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
                'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
            }

            self.custom_edmx_prologue = None
            self.custom_edmx_epilogue = None

            self.custom_data_services_prologue = None
            self.custom_data_services_epilogue = None

            self._reference = '\n<edmx:Reference xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Uri="https://example.sap.corp/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/Vocabularies(TechnicalName=\'%2FIWBEP%2FVOC_COMMON\',Version=\'0001\',SAP__Origin=\'LOCAL\')/$value">' + \
                              '\n<edmx:Include Namespace="com.sap.vocabularies.Common.v1" Alias="Common"/>' + \
                              '\n</edmx:Reference>'

            self._schemas = ''

        def add_schema(self, namespace, xml_definition):
            """Add schema element"""
            self._schemas += f""""\n<Schema xmlns:d="{self.namespaces["d"]}" xmlns:m="{self.namespaces["m"]}" xmlns="{
            self.namespaces["edm"]}" Namespace="{namespace}" xml:lang="en" sap:schema-version="1">"""
            self._schemas += "\n" + xml_definition
            self._schemas += '\n</Schema>'

        def serialize(self):
            """Returns full metadata XML document"""
            result = self._edmx_prologue()

            if self.reference_is_enabled:
                result += self._reference

            if self.data_services_is_enabled:
                result += self._data_services_prologue()

            if self.schema_is_enabled:
                result += self._schemas

            if self.data_services_is_enabled:
                result += self._data_services_epilogue()

            result += self._edmx_epilogue()

            return result

        def _edmx_prologue(self):
            if self.custom_edmx_prologue:
                prologue = self.custom_edmx_prologue
            else:
                prologue = f"""<edmx:Edmx  xmlns:edmx="{self.namespaces["edmx"]}" xmlns:m="{self.namespaces["m"]}" xmlns:sap="{self.namespaces["sap"]}" Version="1.0">"""
            return prologue

        def _edmx_epilogue(self):
            if self.custom_edmx_epilogue:
                epilogue = self.custom_edmx_epilogue
            else:
                epilogue = '\n</edmx:Edmx>'
            return epilogue

        def _data_services_prologue(self):
            if self.custom_data_services_prologue:
                prologue = self.custom_data_services_prologue
            else:
                prologue = '\n<edmx:DataServices m:DataServiceVersion="2.0">'
            return prologue

        def _data_services_epilogue(self):
            if self.custom_data_services_epilogue:
                prologue = self.custom_data_services_epilogue
            else:
                prologue = '\n</edmx:DataServices>'
            return prologue

    return XMLBuilder


@pytest.fixture
def schema(metadata):
    """Parsed metadata"""

    # pylint: disable=redefined-outer-name

    return schema_from_xml(metadata)


def assert_logging_policy(mock_warning, *args):
    """Assert if an warning was outputted by PolicyWarning """
    assert logging.Logger.warning is mock_warning
    mock_warning.assert_called_with('[%s] %s', *args)


def assert_request_contains_header(headers, name, value):
    assert name in headers
    assert headers[name] == value


@pytest.fixture
def type_date_time():
    return Types.from_name('Edm.DateTime')


@pytest.fixture
def type_date_time_offset():
    return Types.from_name('Edm.DateTimeOffset')
