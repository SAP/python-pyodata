"""Opt-in grouping must preserve the meaning of combined filter conditions (V4)."""

import ast
import re

import pytest
import requests
import responses

from pyodata.v4.service import FilterExpression as Q, Service


URL_ROOT = 'http://odatapy.example.com'


ROWS = [
    {'ID': 1, 'Name': 'Smith', 'Rating': 1},
    {'ID': 2, 'Name': 'Jones', 'Rating': 2},
    {'ID': 3, 'Name': 'Smith', 'Rating': 2},
    {'ID': 4, 'Name': 'Jones', 'Rating': 1},
    {'ID': 5, 'Name': 'Smith', 'Rating': 9},
    {'ID': 6, 'Name': 'Müller', 'Rating': 3},
]


@pytest.fixture
def products(schema_v4):
    """Build requests without making an HTTP connection."""
    return Service(URL_ROOT, schema_v4, requests).entity_sets.Products.get_entities()


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
        lambda request: request.filter(Q(ID=1) | Q(Rating=2), Name='Smith', group=True),
        {1, 3}, "((Name eq 'Smith') and ((ID eq 1) or (Rating eq 2)))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28Name+eq+%27Smith%27%29+and+%28%28ID+eq+1%29+or+%28Rating+eq+2%29%29%29',
        id='or-with-keyword'),
    pytest.param(
        lambda request: request.filter(ID__in=[2, 3], Name='Smith', group=True),
        {3}, "((ID eq 2 or ID eq 3) and (Name eq 'Smith'))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28ID+eq+2+or+ID+eq+3%29+and+%28Name+eq+%27Smith%27%29%29',
        id='in-with-keyword'),
    pytest.param(
        lambda request: request.filter(Q(ID__in=[2, 3], Name='Smith'), group=True),
        {3}, "((ID eq 2 or ID eq 3) and (Name eq 'Smith'))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28ID+eq+2+or+ID+eq+3%29+and+%28Name+eq+%27Smith%27%29%29',
        id='in-within-q'),
    pytest.param(
        lambda request: request.filter(Q(ID__in=[2, 3], Name='Smith') | Q(ID=5), group=True),
        {3, 5}, "(((ID eq 2 or ID eq 3) and (Name eq 'Smith')) or (ID eq 5))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28%28ID+eq+2+or+ID+eq+3%29+and+%28Name+eq+%27Smith%27%29%29+or+%28ID+eq+5%29%29',
        id='compound-or'),
    pytest.param(
        lambda request: request.filter(Q(ID__in=[2, 3]) & Q(Name='Smith'), group=True),
        {3}, "((ID eq 2 or ID eq 3) and (Name eq 'Smith'))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28ID+eq+2+or+ID+eq+3%29+and+%28Name+eq+%27Smith%27%29%29',
        id='binary-and'),
    pytest.param(
        lambda request: request.filter(Q(ID=2) | Q(ID=3), Q(Name='Smith'), group=True),
        {3}, "(((ID eq 2) or (ID eq 3)) and (Name eq 'Smith'))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28%28ID+eq+2%29+or+%28ID+eq+3%29%29+and+%28Name+eq+%27Smith%27%29%29',
        id='multiple-q'),
    pytest.param(
        lambda request: request.filter(Q(ID=2) | Q(ID=3)).filter(Name='Smith', group=True),
        {3}, "((ID eq 2) or (ID eq 3)) and (Name eq 'Smith')",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28ID+eq+2%29+or+%28ID+eq+3%29%29+and+%28Name+eq+%27Smith%27%29',
        id='group-previous-call'),
    pytest.param(
        lambda request: request.filter(ID__in=[2, 3], group=True).filter(Name='Smith'),
        {3}, "(ID eq 2 or ID eq 3) and Name eq 'Smith'",
        'http://odatapy.example.com/Products?%24filter='
        '%28ID+eq+2+or+ID+eq+3%29+and+Name+eq+%27Smith%27',
        id='group-before-legacy-tail'),
    pytest.param(
        lambda request: request.filter('ID eq 2 or ID eq 3').filter(Name='Smith', group=True),
        {3}, "(ID eq 2 or ID eq 3) and (Name eq 'Smith')",
        'http://odatapy.example.com/Products?%24filter='
        '%28ID+eq+2+or+ID+eq+3%29+and+%28Name+eq+%27Smith%27%29',
        id='raw-before-group'),
    pytest.param(
        lambda request: request.filter('ID eq 2 or ID eq 3', group=True),
        {2, 3}, '(ID eq 2 or ID eq 3)',
        'http://odatapy.example.com/Products?%24filter=%28ID+eq+2+or+ID+eq+3%29',
        id='raw-group'),
    pytest.param(
        lambda request: request.filter(ID=2).filter('ID eq 3', group=True),
        {3}, '(ID eq 3)',
        'http://odatapy.example.com/Products?%24filter=%28ID+eq+3%29',
        id='raw-replaces-previous'),
    pytest.param(
        lambda request: request.filter(Name='Müller', ID=6, group=True),
        {6}, "((Name eq 'Müller') and (ID eq 6))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28Name+eq+%27M%C3%BCller%27%29+and+%28ID+eq+6%29%29',
        id='unicode-encoding'),
    pytest.param(
        lambda request: request.filter(ID__in=[1, 2, 3], group=True)
        .filter(Q(Name='Smith') | Q(Name='Jones'), group=True)
        .filter(Q(Rating=2) | Q(Rating=1), group=True),
        {1, 2, 3},
        "(((ID eq 1 or ID eq 2 or ID eq 3)) and ((Name eq 'Smith') or (Name eq 'Jones')))"
        " and ((Rating eq 2) or (Rating eq 1))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28%28ID+eq+1+or+ID+eq+2+or+ID+eq+3%29%29+and+%28%28Name+eq+%27Smith%27%29'
        '+or+%28Name+eq+%27Jones%27%29%29%29+and+%28%28Rating+eq+2%29+or+%28Rating+eq+1%29%29',
        id='three-grouped-calls'),
    pytest.param(
        lambda request: request.filter(Q(ID=1) | (Q(ID=2) | (Q(ID=3) & Q(Name='Smith'))), group=True),
        {1, 2, 3}, "((ID eq 1) or ((ID eq 2) or ((ID eq 3) and (Name eq 'Smith'))))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28ID+eq+1%29+or+%28%28ID+eq+2%29+or+%28%28ID+eq+3%29+and+%28Name+eq+%27Smith%27%29%29%29%29',
        id='nested-or-and-tail'),
    pytest.param(
        lambda request: request.filter(Q(Name='Smith') & (Q(ID=1) | (Q(ID=3) & Q(Rating=2))), group=True),
        {1, 3}, "((Name eq 'Smith') and ((ID eq 1) or ((ID eq 3) and (Rating eq 2))))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28Name+eq+%27Smith%27%29+and+%28%28ID+eq+1%29+or+%28%28ID+eq+3%29+and+%28Rating+eq+2%29%29%29%29',
        id='and-around-nested-or'),
    pytest.param(
        lambda request: request.filter(Q(ID=1) | (Q(ID=2) & (Q(Name='Smith') | Q(Rating=2))), group=True),
        {1, 2}, "((ID eq 1) or ((ID eq 2) and ((Name eq 'Smith') or (Rating eq 2))))",
        'http://odatapy.example.com/Products?%24filter='
        '%28%28ID+eq+1%29+or+%28%28ID+eq+2%29+and+%28%28Name+eq+%27Smith%27%29+or+%28Rating+eq+2%29%29%29%29',
        id='right-nested-alternating'),
])
@responses.activate
def test_grouped_filter_selects_expected_rows(products, build, expected, expected_filter, expected_url):
    query = build(products)
    expression = query.get_query_params()['$filter']
    assert expression == expected_filter
    assert selected_ids(expression) == expected
    responses.add(responses.GET, expected_url, json={'value': []})
    assert query.execute() == []
    assert responses.calls[0].request.url == expected_url


def test_default_grouping_keeps_legacy_query(products):
    """Existing applications keep their exact query text unless they opt in."""
    expression = products.filter(ID__in=[2, 3], Name='Smith').get_query_params()['$filter']
    assert expression == "ID eq 2 or ID eq 3 and Name eq 'Smith'"
    assert selected_ids(expression) == {2, 3}


def test_empty_grouped_filter_is_a_noop(products):
    assert '$filter' not in products.filter(group=True).get_query_params()
