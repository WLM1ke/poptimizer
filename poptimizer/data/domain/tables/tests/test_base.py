"""Тест логики абстрактного класса таблицы."""
import dataclasses
from datetime import datetime
from typing import List

import pandas as pd
import pytest

from poptimizer.data.domain.tables import base
from poptimizer.shared import domain


def test_create_id():
    """Проверка создание ID."""
    assert base.create_id("f", "g") == domain.ID(base.PACKAGE, "f", "g")


def test_create_id_no_name():
    """Проверка создание ID без указания названия."""
    assert base.create_id("ff") == domain.ID(base.PACKAGE, "ff", "ff")


@dataclasses.dataclass(frozen=True)
class TestEvent(domain.AbstractEvent):
    """Событие для тестового класса."""


class TestTable(base.AbstractTable[TestEvent]):
    """Тестовая таблица.

    Есть атрибут для регулирования обновления.
    """

    group = "test"
    cond = False

    def _update_cond(self, event: TestEvent) -> bool:
        return self.cond

    async def _prepare_df(self, event: TestEvent) -> pd.DataFrame:
        """Для подмены в тестах."""

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Для подмены в тестах."""

    def _new_events(self, event: TestEvent) -> List[domain.AbstractEvent]:
        """Возвращает два события для проверки в тестах."""
        return [TestEvent(), TestEvent()]


def test_wrong_package():
    """Проверка исключения при некорректном указании пакета."""
    id_ = domain.ID("a", "b", "c")
    with pytest.raises(base.TableError):
        TestTable(id_)


def test_wrong_group():
    """Проверка исключения при некорректном указании группе."""
    id_ = domain.ID(base.PACKAGE, "d", "e")
    with pytest.raises(base.TableError):
        TestTable(id_)


@pytest.fixture(scope="function", name="table")
def make_table():
    """Создает пустую тестовую таблицу."""
    id_ = domain.ID(base.PACKAGE, "test", "e")
    return TestTable(id_)


@pytest.mark.asyncio
async def test_not_update(table):
    """Не срабатывание обновления."""
    new_events = await table.handle_event(TestEvent())
    assert isinstance(new_events, list)
    assert not new_events
    assert table._df is None
    assert table._timestamp is None


@pytest.mark.asyncio
async def test_update_table(table, mocker):
    """Не срабатывание обновления."""
    assert table._df is None
    assert table._timestamp is None

    table.cond = True
    mocker.patch.object(table, "_prepare_df")
    mocker.patch.object(table, "_validate_new_df")

    base_time = datetime.utcnow()

    assert await table.handle_event(TestEvent()) == [TestEvent(), TestEvent()]
    assert table._timestamp > base_time
    fake_new_df = table._prepare_df.return_value
    assert table._df is fake_new_df
    table._validate_new_df.assert_called_once_with(fake_new_df)


INDEX_CASES = (
    (pd.DataFrame(index=[3, 2, 1]), True),
    (pd.DataFrame(index=[1, 2, 2]), True),
    (pd.DataFrame(index=[1, 2, 3]), False),
)


@pytest.mark.parametrize("df, raises", INDEX_CASES)
def test_check_unique_increasing_index(df, raises):
    """Проверка возможных случаев проверки индекса."""
    if raises:
        with pytest.raises(base.TableIndexError):
            base.check_unique_increasing_index(df)
    else:
        base.check_unique_increasing_index(df)


DFS_CASES = (
    (
        pd.DataFrame([1, 2]),
        pd.DataFrame([1, 1, 3]),
        True,
    ),
    (
        pd.DataFrame([1, 2]),
        pd.DataFrame([1, 2, 3]),
        False,
    ),
    (
        None,
        pd.DataFrame([1, 2, 3]),
        False,
    ),
)


@pytest.mark.parametrize("df_old, df_new, raises", DFS_CASES)
def test_check_dfs_mismatch(df_old, df_new, raises):
    """Проверка возможных случаев стыков DataFrame."""
    if raises:
        with pytest.raises(base.TableNewDataMismatchError):
            base.check_dfs_mismatch("", df_old, df_new)
    else:
        base.check_dfs_mismatch("", df_old, df_new)
