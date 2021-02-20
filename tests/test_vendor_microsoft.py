"""PyOData Microsoft tests"""

import os
import requests
import pytest
import responses

import pyodata
from pyodata.v2.model import schema_from_xml
from tests.conftest import contents_of_fixtures_file


@pytest.fixture
def metadata_northwind_v2():
    return contents_of_fixtures_file("metadata_odata_org_northwind_v2.xml")


@pytest.fixture
def schema_northwind_v2(metadata_northwind_v2):
    return schema_from_xml(metadata_northwind_v2)


@pytest.fixture
def service_northwind_v2(schema_northwind_v2):
    """https://services.odata.org/V2/Northwind/Northwind.svc/"""
    return pyodata.v2.service.Service('http://not.resolvable.services.odata.org/V2/Northwind/Northwind.svc',
                                      schema_northwind_v2, requests)


@responses.activate
def test_get_entities_with_top_and_skip_without_results_member(service_northwind_v2):
    """Get entities with the missing member results."""

    # pylint: disable=redefined-outer-name

    responses.add(
        responses.GET,
        f"{service_northwind_v2.url}/Employees?$skip=10&$top=5",
        json={'d': [
                {
                    'EmployeeID': 1,
                    'LastName': 'Quellcrist',
                    'FirstName': 'Falconer'
                }
            ]
        },
        status=200)

    empls = service_northwind_v2.entity_sets.Employees.get_entities().skip(10).top(5).execute()
    assert empls[0].EmployeeID == 1
    assert empls[0].LastName == 'Quellcrist'
    assert empls[0].FirstName == 'Falconer'
