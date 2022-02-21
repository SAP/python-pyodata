"""Tests of OData Model: class VariableDeclaration"""

import pytest
from pyodata.v2.model import VariableDeclaration, Types
from pyodata.exceptions import PyODataException


@pytest.fixture
def variable_of_string_nullable():
    variable = VariableDeclaration('TestVariable', Types.parse_type_name('Edm.String'), True, None, None, None, None)
    variable.typ = Types.from_name(variable.type_info.name)
    return variable

@pytest.fixture
def variable_of_string():
    variable = VariableDeclaration('TestVariable', Types.parse_type_name('Edm.String'), False, None, None, None, None)
    variable.typ = Types.from_name(variable.type_info.name)
    return variable


def test_variable_of_string_nullable_from_json_none(variable_of_string_nullable):
    assert variable_of_string_nullable.from_json(None) is None


def test_variable_of_string_nullable_to_json_none(variable_of_string_nullable):
    assert variable_of_string_nullable.to_json(None) is None


def test_variable_of_string_nullable_from_literal_none(variable_of_string_nullable):
    assert variable_of_string_nullable.from_literal(None) is None


def test_variable_of_string_nullable_to_literal_none(variable_of_string_nullable):
    assert variable_of_string_nullable.to_literal(None) is None


def test_variable_of_string_nullable_from_json_non_none(variable_of_string_nullable):
    assert variable_of_string_nullable.from_json('FromJSON') == 'FromJSON'


def test_variable_of_string_nullable_to_json(variable_of_string_nullable):
    assert variable_of_string_nullable.to_json('ToJSON') == 'ToJSON'


def test_variable_of_string_nullable_from_literal(variable_of_string_nullable):
    assert variable_of_string_nullable.from_literal("'FromLiteral'") == 'FromLiteral'


def test_variable_of_string_nullable_to_literal(variable_of_string_nullable):
    assert variable_of_string_nullable.to_literal('ToLiteral') == "'ToLiteral'"


def test_variable_of_string_from_json_none(variable_of_string):
    with pytest.raises(PyODataException) as e_info:
        variable_of_string.from_json(None)
    assert str(e_info.value).startswith('Cannot convert null JSON to value of VariableDeclaration(TestVariable)')


def test_variable_of_string_to_json_none(variable_of_string):
    with pytest.raises(PyODataException) as e_info:
        variable_of_string.to_json(None)
    assert str(e_info.value).startswith('Cannot convert None to JSON of VariableDeclaration(TestVariable)')


def test_variable_of_string_from_literal_none(variable_of_string):
    with pytest.raises(PyODataException) as e_info:
        variable_of_string.from_literal(None)
    assert str(e_info.value).startswith('Cannot convert null URL literal to value of VariableDeclaration(TestVariable)')


def test_variable_of_string_to_literal_none(variable_of_string):
    with pytest.raises(PyODataException) as e_info:
        variable_of_string.to_literal(None)
    assert str(e_info.value).startswith('Cannot convert None to URL literal of VariableDeclaration(TestVariable)')
