"""Тесты для фабрик по созданию таблиц и их сериализации."""
from datetime import datetime

import pandas as pd
import pytest

from poptimizer.data.domain import factories, model
from poptimizer.data.ports import outer

TABLE_NAME = outer.TableName(outer.QUOTES, "VSMO")
TABLE_VARS = outer.TableTuple(
    TABLE_NAME.group,
    TABLE_NAME.name,
    pd.DataFrame([1]),
    datetime.utcnow(),
)


def test_create_table():
    """У новой таблицы не должно быть данных и времени обновления."""
    table = factories.create_table(TABLE_NAME)

    assert isinstance(table, model.Table)
    assert table.df is None
    assert table.timestamp is None


def test_recreate_table():
    """У таблицы должны быть переданные значения данных и времени обновления.

    Данные должны возвращаться копией.
    """
    table = factories.recreate_table(TABLE_VARS)

    assert isinstance(table, model.Table)
    assert table.name == TABLE_NAME

    pd.testing.assert_frame_equal(table.df, TABLE_VARS.df)
    assert table.df is not TABLE_VARS.df
    assert table.timestamp == TABLE_VARS.timestamp

    desc = model.TableDescription(table._loader, table._index_checks, table._validate)
    assert desc == factories._TABLES_REGISTRY[TABLE_NAME.group]


def test_convent_to_tuple():
    """Проверка, что воссозданная и обратно сериализованная таблицы совпадают."""
    table = factories.recreate_table(TABLE_VARS)
    table_vars = factories.convent_to_tuple(table)

    assert table_vars.group == TABLE_VARS.group
    assert table_vars.name == TABLE_VARS.name
    assert table_vars.timestamp == TABLE_VARS.timestamp
    pd.testing.assert_frame_equal(table_vars.df, TABLE_VARS.df)


def test_convent_to_tuple_raises_on_empty_table():
    """Проверка запрета на сериализацию пустой таблицы."""
    table = factories.create_table(TABLE_NAME)

    with pytest.raises(outer.DataError, match="Попытка сериализации пустой таблицы"):
        factories.convent_to_tuple(table)
