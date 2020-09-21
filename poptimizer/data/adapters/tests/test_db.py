"""Тесты для соединения с БД."""
import asyncio
import logging
from datetime import datetime

import pandas as pd
import pytest

from poptimizer.data.adapters import db
from poptimizer.data.config import resources
from poptimizer.data.ports import outer

DF = pd.DataFrame(
    [[5, 6], [6, 7]],
    columns=["s", "f"],
    index=["r", "g"],
)
TIMESTAMP = datetime.utcnow()
TIMESTAMP = TIMESTAMP.replace(microsecond=(TIMESTAMP.microsecond // 1000) * 1000)
TABLE_NAME = outer.TableName(outer.SECURITIES, outer.SECURITIES)
TABLE_TUPLE = outer.TableTuple(outer.SECURITIES, outer.SECURITIES, DF, TIMESTAMP)

NAME_CASES = (
    [outer.TableTuple(outer.QUOTES, "VTBR", DF, TIMESTAMP), outer.QUOTES, "VTBR"],
    [outer.TableName(outer.QUOTES, "HYDR"), outer.QUOTES, "HYDR"],
    [TABLE_TUPLE, db.MISC, outer.SECURITIES],
    [TABLE_NAME, db.MISC, outer.SECURITIES],
)


@pytest.mark.parametrize("table_name, collection, name", NAME_CASES)
def test_collection_and_name(table_name, collection, name):
    """Тестирование комбинации двух пар случаев.

    - Сохранение или загрузка
    - Использование отдельной коллекции или коллекции для прочих данных
    """
    assert db._collection_and_name(table_name) == (collection, name)


@pytest.fixture(scope="module", name="mongo")
@pytest.mark.asyncio
async def create_mongo_db():
    """Создание тестовой БД."""
    client = resources.MONGO_CLIENT
    yield client["test"]
    await client.drop_database("test")


@pytest.mark.asyncio
async def test_mongo_db_session_get_none(mongo):
    """Загрузка отсутствующего документа."""
    collection = mongo[db.MISC]
    assert await collection.count_documents({}) == 0
    assert await db.MongoDBSession(mongo).get(TABLE_NAME) is None
    assert await collection.count_documents({}) == 0


@pytest.mark.asyncio
async def test_mongo_db_session_get_commit(mongo, caplog):
    """Сохранение таблицы."""
    caplog.set_level(logging.INFO)

    await db.MongoDBSession(mongo).commit([TABLE_TUPLE])
    assert await mongo[db.MISC].count_documents({}) == 1

    await asyncio.sleep(0.01)
    assert caplog.record_tuples == [
        (
            "MongoDBSession",
            20,
            "Сохранение misc.securities",
        ),
    ]


@pytest.mark.asyncio
async def test_mongo_db_session_get_table(mongo):
    """Загрузка ранее сохраненной таблицы."""
    table_tuple = await db.MongoDBSession(mongo).get(TABLE_NAME)

    assert table_tuple.group == TABLE_TUPLE.group
    assert table_tuple.name == TABLE_TUPLE.group
    pd.testing.assert_frame_equal(table_tuple.df, TABLE_TUPLE.df)
    assert table_tuple.timestamp == TABLE_TUPLE.timestamp
    assert await mongo[db.MISC].count_documents({}) == 1
