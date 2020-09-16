"""Тесты для таблицы с данными."""
from datetime import datetime
from typing import Optional, cast

import pandas as pd
import pytest

from poptimizer.data.domain import model
from poptimizer.data.ports import outer

TABLE_NAME = outer.TableName(outer.QUOTES, "GAZP")
DF = pd.DataFrame(
    [1, 2],
    index=[datetime(2020, 9, 9), datetime(2020, 9, 10)],
)
DF_LOADER = pd.DataFrame([1])
DF_INCREMENTAL_LOADER = pd.DataFrame(
    [4, 3],
    index=[
        datetime(2020, 9, 10),
        datetime(2020, 9, 11),
    ],
)
DF_RESULT = pd.DataFrame(
    [1, 4, 3],
    index=[
        datetime(2020, 9, 9),
        datetime(2020, 9, 10),
        datetime(2020, 9, 11),
    ],
)


class TestLoader(outer.AbstractLoader):
    """Тестовая реализация загрузчика данных."""

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получить обновление."""
        return DF_LOADER


class TestIncrementalLoader(outer.AbstractIncrementalLoader):
    """Тестовая реализация инкрементального загрузчика данных."""

    async def get(
        self,
        table_name: outer.TableName,
        last_index: Optional[str] = None,
    ) -> pd.DataFrame:
        """Получить обновление."""
        return DF_INCREMENTAL_LOADER


@pytest.fixture(scope="function", name="empty_table")
def make_empty_table():
    """Создание пустой таблицы для тестов."""
    return model.Table(
        name=TABLE_NAME,
        desc=model.TableDescription(
            loader=TestLoader(),
            index_checks=model.IndexChecks.NO_CHECKS,
            validate=False,
        ),
    )


def test_table_no_df(empty_table):
    """Пустая таблица не должна содержать данные и дату обновления."""
    assert empty_table.name == TABLE_NAME
    assert empty_table.df is None
    assert empty_table.timestamp is None


def test_table_df_copy():
    """Таблица должна возвращать одинаковые копии DataFrame."""
    table = model.Table(
        name=TABLE_NAME,
        desc=model.TableDescription(
            loader=TestLoader(),
            index_checks=model.IndexChecks.NO_CHECKS,
            validate=False,
        ),
        df=DF,
        timestamp=datetime.utcnow(),
    )

    pd.testing.assert_frame_equal(table.df, DF)
    pd.testing.assert_frame_equal(table.df, table.df)
    assert table.df is not table.df


TIMESTAMP = datetime(2020, 9, 11)
END_OF_TRADING_DAY = datetime(2020, 9, 12)
UPDATE_COND_CASES = (
    (None, END_OF_TRADING_DAY, True),
    (TIMESTAMP, None, True),
    (TIMESTAMP, END_OF_TRADING_DAY, True),
    (END_OF_TRADING_DAY, TIMESTAMP, False),
)


@pytest.mark.parametrize("timestamp, end_of_trading_day, update_cond", UPDATE_COND_CASES)
def test_update_cond(timestamp, end_of_trading_day, update_cond):
    """Проверка условия на необходимость обновления.

    Должны обновляться:
    - отсутствующие данные
    - при отсутствующем конце торгового дня
    - данные в последний раз обновлялись до конца торгового дня
    """
    assert model._update_cond(timestamp, end_of_trading_day) is update_cond


PREPARE_DF_CASES = (
    (TABLE_NAME, None, TestIncrementalLoader(), DF_INCREMENTAL_LOADER),
    (TABLE_NAME, pd.DataFrame(), TestIncrementalLoader(), DF_INCREMENTAL_LOADER),
    (TABLE_NAME, DF, TestLoader(), DF_LOADER),
    (TABLE_NAME, DF, TestIncrementalLoader(), DF_RESULT),
)


@pytest.mark.parametrize("name, df, loader, df_result", PREPARE_DF_CASES)
@pytest.mark.asyncio
async def test_prepare_df(name, df, loader, df_result):
    """Обработка различных вариантов обновления.

    Существует 3 случая обновления полностью - при отсутствии данных, при пустых данных и для данных
    обновляемых только полностью.

    Один вариант инкрементального обновления - должны присутствовать не пустые предыдущие данные и
    поддерживаться инкрементальное обновление.
    """
    df_new = await model._prepare_df(name, df, loader)

    pd.testing.assert_frame_equal(df_result, df_new)


DF_OLD = pd.DataFrame([1, 2], index=[0, 1])
DF_NEW_GOOD = pd.DataFrame([1, 2, 3], index=[0, 1, 2])
DF_NEW_BAD = pd.DataFrame([1, -1, 3], index=[0, 1, 2])
VALIDATE_DATA_CASES = (
    (False, DF_OLD, DF_NEW_BAD, False),
    (True, None, DF_NEW_BAD, False),
    (True, DF_OLD, DF_NEW_GOOD, False),
    (True, DF_OLD, DF_NEW_BAD, True),
)


@pytest.mark.parametrize("validate, df_old, df_new, raises", VALIDATE_DATA_CASES)
def test_validate_data(validate, df_old, df_new, raises):
    """Проверка совпадения старых и новых данных.

    Не должно срабатывать исключение, если проверка отключена или старые и новые данные совпадают для
    старого индекса.
    """
    if raises:
        with pytest.raises(outer.DataError, match="Новые данные не соответствуют старым"):
            model._validate_data(validate, df_old, df_new)
    else:
        model._validate_data(validate, df_old, df_new)


CHECK_INDEX_CASES = (
    (model.IndexChecks.NO_CHECKS, pd.Index([0, 1, 1]), False),
    (model.IndexChecks.NO_CHECKS, pd.Index([2, 1, 3]), False),
    (model.IndexChecks.UNIQUE, pd.Index([2, 1, 3]), False),
    (model.IndexChecks.UNIQUE, pd.Index([0, 1, 1]), True),
    (model.IndexChecks.ASCENDING, pd.Index([2, 1, 3]), True),
    (model.IndexChecks.ASCENDING, pd.Index([0, 1, 1]), False),
    (model.IndexChecks.UNIQUE_ASCENDING, pd.Index([2, 1, 3]), True),
    (model.IndexChecks.UNIQUE_ASCENDING, pd.Index([0, 1, 1]), True),
    (model.IndexChecks.UNIQUE_ASCENDING, pd.Index([1, 2, 3]), False),
)


@pytest.mark.parametrize("check, index, raises", CHECK_INDEX_CASES)
def test_check_index(check, index, raises):
    """Тестирование вариантов проверки индекса.

    Варианты подобраны, так чтобы случаи:

     - пропускаемые более строгими вариантами, срабатывали на более сильных
     - пропускаемые аналогичными по строгости, срабатывали на других аналогах
    """
    if raises:
        with pytest.raises(outer.DataError, match="Индекс не"):
            model._check_index(check, index)
    else:
        model._check_index(check, index)


@pytest.mark.asyncio
async def test_table_update(empty_table):
    """Тестирование полного цикла обновления.

    - Обновление пустой таблицы
    - Не осуществление обновления таблицы, которая обновлялась после после конца торгового дня
    - Обновление не пустой таблицы
    """
    assert empty_table.df is None
    assert empty_table.timestamp is None

    now = datetime.utcnow()
    await empty_table.update(None)
    pd.testing.assert_frame_equal(DF_LOADER, empty_table.df)
    timestamp = empty_table.timestamp
    assert cast(datetime, timestamp) > now

    await empty_table.update(now)
    assert empty_table.timestamp == timestamp

    now = datetime.utcnow()
    await empty_table.update(now)
    timestamp = empty_table.timestamp
    assert cast(datetime, timestamp) > now
