"""Tests for OData V4 Model module"""
# pylint: disable=redefined-outer-name,line-too-long,invalid-name

import datetime

import pytest

import pyodata.v2.model
import pyodata.v4.model
from pyodata.v4.model import MetadataBuilder, Types
from pyodata.exceptions import PyODataParserError
from tests.conftest import contents_of_fixtures_file


def test_v4_type_traits_roundtrip():
    """All V4 primitive traits round-trip through from_json/to_json and from_literal/to_literal"""

    # Edm.Boolean
    boolean = Types.from_name('Edm.Boolean').traits
    assert boolean.from_json(boolean.to_json(True)) is True
    assert boolean.from_literal(boolean.to_literal(False)) is False

    # Edm.String
    string = Types.from_name('Edm.String').traits
    assert string.from_json(string.to_json('hello')) == 'hello'
    assert string.from_literal(string.to_literal('world')) == 'world'

    # Edm.Int64
    int64 = Types.from_name('Edm.Int64').traits
    assert int64.from_json(int64.to_json(42)) == 42
    assert int64.to_literal(42) == '42'
    assert int64.from_literal(int64.to_literal(7)) == 7

    # Edm.Decimal (pass-through as str)
    decimal = Types.from_name('Edm.Decimal').traits
    assert decimal.from_json(decimal.to_json('3.14')) == '3.14'
    assert decimal.from_literal(decimal.to_literal('2.5')) == '2.5'

    # Edm.Date
    date = Types.from_name('Edm.Date').traits
    value = datetime.date(2020, 1, 31)
    assert date.from_json(date.to_json(value)) == value
    assert date.from_literal(date.to_literal(value)) == value
    assert date.to_literal(value) == '2020-01-31'

    # Edm.TimeOfDay
    time_of_day = Types.from_name('Edm.TimeOfDay').traits
    time_value = datetime.time(13, 45, 30)
    assert time_of_day.from_json(time_of_day.to_json(time_value)) == time_value
    assert time_of_day.from_literal(time_of_day.to_literal(time_value)) == time_value

    # Edm.Duration
    duration = Types.from_name('Edm.Duration').traits
    delta = datetime.timedelta(hours=1, minutes=30)
    assert duration.from_json(duration.to_json(delta)) == delta
    assert duration.from_literal(duration.to_literal(delta)) == delta

    # Edm.DateTimeOffset
    dto = Types.from_name('Edm.DateTimeOffset').traits
    stamp = datetime.datetime(2020, 1, 31, 10, 20, 30, tzinfo=datetime.timezone.utc)
    assert dto.from_json(dto.to_json(stamp)) == stamp
    assert dto.from_literal(dto.to_literal(stamp)) == stamp


def test_edm_datetime_absent_from_v4_types():
    """Edm.DateTime is not part of the V4 Types registry"""

    with pytest.raises(KeyError):
        Types.from_name('Edm.DateTime')


def test_v4_and_v2_types_are_independent():
    """V4 Types and V2 Types are distinct class objects with independent registries"""

    assert pyodata.v4.model.Types is not pyodata.v2.model.Types

    # Edm.DateTime exists in V2 but not in V4; proves separate registries.
    assert pyodata.v2.model.Types.from_name('Edm.DateTime') is not None
    with pytest.raises(KeyError):
        pyodata.v4.model.Types.from_name('Edm.DateTime')


def test_v4_edmx_parses(schema_v4):
    """A V4 EDMX document parses into a valid schema"""

    assert schema_v4.is_valid is True
    assert 'Northwind' in schema_v4.namespaces


def test_v2_edmx_rejected_by_v4_builder():
    """A V2 EDMX document fed to the V4 MetadataBuilder raises PyODataParserError"""

    v2_metadata = contents_of_fixtures_file('metadata.xml')
    with pytest.raises(PyODataParserError):
        MetadataBuilder(v2_metadata).build()


def test_navigation_property_type_and_partner(schema_v4):
    """V4 nav properties are parsed from Type=/Partner=, not Relationship="""

    product = schema_v4.entity_type('Product')
    category_nav = product.nav_proprty('Category')

    assert category_nav.partner == 'Products'
    assert category_nav.typ is schema_v4.entity_type('Category')

    # No V2 association concept on V4 navigation properties.
    assert not hasattr(category_nav, 'association')
    assert not hasattr(category_nav, 'to_role')
    assert not hasattr(category_nav, 'from_role')


def test_navigation_property_contains_target(schema_v4):
    """ContainsTarget= is parsed into contains_target"""

    product = schema_v4.entity_type('Product')
    category = schema_v4.entity_type('Category')

    assert product.nav_proprty('Supplier').contains_target is True
    assert category.nav_proprty('Products').contains_target is False


def test_entity_type_base_type_inheritance(schema_v4):
    """Supplier inherits from Category via BaseType="""

    supplier = schema_v4.entity_type('Supplier')
    category = schema_v4.entity_type('Category')

    assert supplier.base_type == f'Northwind.{category.name}'
    assert supplier.proprty('Phone') is not None


def test_singleton_present(schema_v4):
    """Singleton BestSeller is present and typed"""

    best_seller = schema_v4.singleton('BestSeller')
    assert best_seller.name == 'BestSeller'
    assert best_seller.entity_type is schema_v4.entity_type('Product')
    assert best_seller in schema_v4.singletons


def test_action_is_bound(schema_v4):
    """Action binding is parsed; parameters are accessible"""

    discount = schema_v4.action('Discount')
    reset_all = schema_v4.action('ResetAll')

    assert discount.is_bound is True
    assert reset_all.is_bound is False

    assert {p.name for p in discount.parameters} == {'product', 'percent'}
    assert discount.get_parameter('percent').name == 'percent'


def test_schema_has_no_association(schema_v4):
    """V4 Schema exposes no association concept"""

    assert not hasattr(schema_v4, 'association')
    assert not hasattr(schema_v4, 'associations')


def test_decimal_scale_variable(schema_v4):
    """Scale='variable' is accepted on an Edm.Decimal property"""

    product = schema_v4.entity_type('Product')
    assert product.proprty('Price').scale == 'variable'


def test_shared_and_fresh_classes():
    """Classes imported from v2 are the same objects; Types is fresh"""

    assert pyodata.v4.model.ErrorPolicy is pyodata.v2.model.ErrorPolicy
    assert pyodata.v4.model.Config is pyodata.v2.model.Config
    assert pyodata.v4.model.TypeInfo is pyodata.v2.model.TypeInfo

    # Types is a fresh, independent class.
    assert pyodata.v4.model.Types is not pyodata.v2.model.Types


def test_function_and_action_import_resolution(schema_v4):
    """FunctionImport/ActionImport resolve to their Function/Action"""

    func_import = schema_v4.function_import('BestProduct')
    assert func_import.function is schema_v4.function('BestProduct')

    action_import = schema_v4.action_import('ResetAll')
    assert action_import.action is schema_v4.action('ResetAll')


def test_open_type(schema_v4):
    """OpenType attribute is parsed onto entity types"""

    assert schema_v4.entity_type('Product').open_type is True
    assert schema_v4.entity_type('Category').open_type is False
