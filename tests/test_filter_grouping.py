"""Opt-in grouping must preserve the meaning of combined filter conditions."""

import ast
import re

import pytest
import requests
import responses

from pyodata.v2.service import FilterExpression as Q, Service


ROWS = [
    {'ID': 1, 'NameLast': 'Smith', 'NickName': 'Al'},
    {'ID': 2, 'NameLast': 'Jones', 'NickName': 'Tim'},
    {'ID': 3, 'NameLast': 'Smith', 'NickName': 'Tim'},
    {'ID': 4, 'NameLast': 'Jones', 'NickName': 'Al'},
    {'ID': 5, 'NameLast': 'Smith', 'NickName': 'Other'},
    {'ID': 6, 'NameLast': 'Müller', 'NickName': 'René'},
]


@pytest.fixture
def employees(schema):
    """Build requests without making an HTTP connection."""
    return Service('http://odata.example.com', schema, requests).entity_sets.Employees.get_entities()


def selected_ids(expression):
    """Use Python's independent parser for the tested eq/and/or OData subset."""
    tree = ast.parse(re.sub(r'\beq\b', '==', expression), mode='eval')

    def evaluate(node, row):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return row[node.id]
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            return evaluate(node.left, row) == evaluate(node.comparators[0], row)
        if isinstance(node, ast.BoolOp):
            values = (evaluate(value, row) for value in node.values)
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
        raise AssertionError(f'Unexpected filter node: {ast.dump(node)}')

    return {row['ID'] for row in ROWS if evaluate(tree.body, row)}


@pytest.mark.parametrize('build, expected, expected_filter, expected_url', [
    pytest.param(
        lambda request: request.filter(Q(ID=1) | Q(NickName='Tim'), NameLast='Smith', group=True),
        {1, 3}, "((NameLast eq 'Smith') and ((ID eq 1) or (NickName eq 'Tim')))",
        'http://odata.example.com/Employees?%24filter='
        '%28%28NameLast+eq+%27Smith%27%29+and+%28%28ID+eq+1%29+or+%28NickName+eq+%27Tim%27%29%29%29',
        id='or-with-keyword'),
    pytest.param(
        lambda request: request.filter(ID__in=[2, 3], NameLast='Smith', group=True),
        {3}, "((ID eq 2 or ID eq 3) and (NameLast eq 'Smith'))",
        'http://odata.example.com/Employees?%24filter='
        '%28%28ID+eq+2+or+ID+eq+3%29+and+%28NameLast+eq+%27Smith%27%29%29',
        id='in-with-keyword'),
    pytest.param(
        lambda request: request.filter(Q(ID__in=[2, 3], NameLast='Smith'), group=True),
        {3}, "((ID eq 2 or ID eq 3) and (NameLast eq 'Smith'))",
        'http://odata.example.com/Employees?%24filter='
        '%28%28ID+eq+2+or+ID+eq+3%29+and+%28NameLast+eq+%27Smith%27%29%29',
        id='in-within-q'),
    pytest.param(
        lambda request: request.filter(Q(ID__in=[2, 3], NameLast='Smith') | Q(ID=5), group=True),
        {3, 5}, "(((ID eq 2 or ID eq 3) and (NameLast eq 'Smith')) or (ID eq 5))",
        'http://odata.example.com/Employees?%24filter='
        '%28%28%28ID+eq+2+or+ID+eq+3%29+and+%28NameLast+eq+%27Smith%27%29%29+or+%28ID+eq+5%29%29',
        id='compound-or'),
    pytest.param(
        lambda request: request.filter(Q(ID__in=[2, 3]) & Q(NameLast='Smith'), group=True),
        {3}, "((ID eq 2 or ID eq 3) and (NameLast eq 'Smith'))",
        'http://odata.example.com/Employees?%24filter='
        '%28%28ID+eq+2+or+ID+eq+3%29+and+%28NameLast+eq+%27Smith%27%29%29',
        id='binary-and'),
    pytest.param(
        lambda request: request.filter(Q(ID=2) | Q(ID=3), Q(NameLast='Smith'), group=True),
        {3}, "(((ID eq 2) or (ID eq 3)) and (NameLast eq 'Smith'))",
        'http://odata.example.com/Employees?%24filter='
        '%28%28%28ID+eq+2%29+or+%28ID+eq+3%29%29+and+%28NameLast+eq+%27Smith%27%29%29',
        id='multiple-q'),
    pytest.param(
        lambda request: request.filter(Q(ID=2) | Q(ID=3)).filter(NameLast='Smith', group=True),
        {3}, "((ID eq 2) or (ID eq 3)) and (NameLast eq 'Smith')",
        'http://odata.example.com/Employees?%24filter='
        '%28%28ID+eq+2%29+or+%28ID+eq+3%29%29+and+%28NameLast+eq+%27Smith%27%29',
        id='group-previous-call'),
    pytest.param(
        lambda request: request.filter(ID__in=[2, 3], group=True).filter(NameLast='Smith'),
        {3}, "(ID eq 2 or ID eq 3) and NameLast eq 'Smith'",
        'http://odata.example.com/Employees?%24filter='
        '%28ID+eq+2+or+ID+eq+3%29+and+NameLast+eq+%27Smith%27',
        id='group-before-legacy-tail'),
    pytest.param(
        lambda request: request.filter('ID eq 2 or ID eq 3').filter(NameLast='Smith', group=True),
        {3}, "(ID eq 2 or ID eq 3) and (NameLast eq 'Smith')",
        'http://odata.example.com/Employees?%24filter='
        '%28ID+eq+2+or+ID+eq+3%29+and+%28NameLast+eq+%27Smith%27%29',
        id='raw-before-group'),
    pytest.param(
        lambda request: request.filter('ID eq 2 or ID eq 3', group=True),
        {2, 3}, '(ID eq 2 or ID eq 3)',
        'http://odata.example.com/Employees?%24filter=%28ID+eq+2+or+ID+eq+3%29',
        id='raw-group'),
    pytest.param(
        lambda request: request.filter(ID=2).filter('ID eq 3', group=True),
        {3}, '(ID eq 3)',
        'http://odata.example.com/Employees?%24filter=%28ID+eq+3%29',
        id='raw-replaces-previous'),
    pytest.param(
        lambda request: request.filter(NameLast='Müller', NickName='René', group=True),
        {6}, "((NameLast eq 'Müller') and (NickName eq 'René'))",
        'http://odata.example.com/Employees?%24filter='
        '%28%28NameLast+eq+%27M%C3%BCller%27%29+and+%28NickName+eq+%27Ren%C3%A9%27%29%29',
        id='unicode-encoding'),
])
@responses.activate
def test_grouped_filter_selects_expected_rows(employees, build, expected, expected_filter, expected_url):
    query = build(employees)
    expression = query.get_query_params()['$filter']
    assert expression == expected_filter
    assert selected_ids(expression) == expected
    responses.add(responses.GET, expected_url, json={'d': {'results': []}})
    assert query.execute() == []
    assert responses.calls[0].request.url == expected_url


def test_default_grouping_keeps_legacy_query(employees):
    """Existing applications keep their exact query text unless they opt in."""
    expression = employees.filter(ID__in=[2, 3], NameLast='Smith').get_query_params()['$filter']
    assert expression == "ID eq 2 or ID eq 3 and NameLast eq 'Smith'"
    assert selected_ids(expression) == {2, 3}


def test_empty_grouped_filter_is_a_noop(employees):
    assert '$filter' not in employees.filter(group=True).get_query_params()
