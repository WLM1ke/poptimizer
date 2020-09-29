"""Тесты для Репо."""
import asyncio
import random
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd
import pytest

from poptimizer.data.domain import model, repo
from poptimizer.data.ports import outer

TABLE_NAME = outer.TableName(outer.QUOTES, "VSMO")
DF = pd.DataFrame([20])
TIMESTAMP = datetime.utcnow()


class FakeSession(outer.AbstractDBSession):
    """Сессия для тестирования."""

    def __init__(self, tables_vars=None, random_wait=False):
        """Таблицы, которые есть в репо."""
        self.random = random_wait
        self.tables = {}
        if tables_vars is not None:
            self.tables = {(table.group, table.name): table for table in tables_vars}

    async def get(self, table_name: outer.TableName) -> Optional[outer.TableTuple]:
        """Дает таблицу из хранилища."""
        if self.random:
            await asyncio.sleep(random.random())  # noqa: S311
        return self.tables.get(table_name)

    async def commit(self, tables_vars: Iterable[outer.TableTuple]) -> None:
        """Сохраняет таблицу в хранилище."""
        for table in tables_vars:
            self.tables[(table.group, table.name)] = table


@pytest.mark.asyncio
async def test_repo_loads_concurrent_identity():
    """Разные репо возвращают одну и туже таблицу при конкурентном доступе."""
    session = FakeSession(random_wait=True)
    table_gets = [repo.Repo(session).get_table(TABLE_NAME) for _ in range(100)]
    first, *others = await asyncio.gather(*table_gets)
    for table in others:
        assert first is table


@pytest.mark.asyncio
async def test_repo_free_identity_map_and_timestamps():
    """Освобождение ресурсов после окончания использования таблицы и репо."""
    assert not repo.Repo._identity_map

    store = repo.Repo(FakeSession())
    table = await store.get_table(TABLE_NAME)

    assert repo.Repo._identity_map

    del table  # noqa: WPS420

    assert repo.Repo._identity_map

    del store  # noqa: WPS420

    assert not repo.Repo._identity_map


@pytest.mark.asyncio
async def test_repo_not_commit_not_changed_table():
    """Если таблица не изменилась после загрузки, то она не сохраняется в БД."""
    session = FakeSession()

    async with repo.Repo(session) as store:
        table = await store.get_table(TABLE_NAME)

        assert isinstance(table, model.Table)
        assert table.name == TABLE_NAME
        assert table.df is None
        assert table.timestamp is None

    assert not session.tables


@pytest.mark.asyncio
async def test_repo_commit_changed_table():
    """Измененная таблица сохраняется в базу данных."""
    session = FakeSession()

    async with repo.Repo(session) as store:
        table = await store.get_table(TABLE_NAME)

        table._timestamp = TIMESTAMP
        table._df = DF

    assert len(session.tables) == 1
    table_vars = session.tables[TABLE_NAME]
    assert isinstance(table_vars, outer.TableTuple)
    assert table_vars.timestamp == TIMESTAMP
    pd.testing.assert_frame_equal(table_vars.df, DF)


@pytest.mark.asyncio
async def test_repo_commit_changed_table_one_time():
    """Измененная таблица сохраняется в базу данных один раз из нескольких репо."""
    session = FakeSession()

    async with repo.Repo(session) as store_outer:
        table_outer = await store_outer.get_table(TABLE_NAME)

        async with repo.Repo(session) as store:
            table = await store.get_table(TABLE_NAME)

            table._timestamp = TIMESTAMP
            table._df = DF

        assert len(session.tables) == 1
        session.tables.clear()

        assert table_outer.timestamp == TIMESTAMP
        pd.testing.assert_frame_equal(table_outer.df, DF)

    assert not session.tables


@pytest.mark.asyncio
async def test_repo_loads_from_db():
    """Измененная таблица сохраняется в базу данных один раз из нескольких репо."""
    session = FakeSession([outer.TableTuple(*TABLE_NAME, DF, TIMESTAMP)])
    store = repo.Repo(session)
    table = await store.get_table(TABLE_NAME)

    assert isinstance(table, model.Table)
    assert table.name == TABLE_NAME
    pd.testing.assert_frame_equal(table.df, DF)
    assert table.timestamp == TIMESTAMP
