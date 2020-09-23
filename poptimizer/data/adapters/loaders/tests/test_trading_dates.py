"""Тесты загрузки таблицы с диапазоном торговых дат."""
import asyncio
import logging
import random

import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import trading_dates
from poptimizer.data.config import resources
from poptimizer.data.ports import outer

LOGGER_CLASS_NAME = "TradingDatesLoader"
TABLE_NAME = outer.TableName(outer.TRADING_DATES, outer.TRADING_DATES)
JSON = ({"from": "1997-03-24", "till": "2020-09-22"},)
DF = pd.DataFrame(JSON, dtype="datetime64[ns]")

NAMES_CASES = (
    outer.TableName(outer.TRADING_DATES, "test"),
    outer.TableName(outer.QUOTES, outer.TRADING_DATES),
)


@pytest.mark.parametrize("table_name", NAMES_CASES)
@pytest.mark.asyncio
async def test_raise_on_wrong_name(table_name):
    """Не верное название данных."""
    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        loader = trading_dates.TradingDatesLoader()
        await loader.get(table_name)


@pytest.mark.asyncio
async def test_get_df(mocker, caplog):
    """Загрузка данных."""
    caplog.set_level(logging.INFO)
    outer_call = mocker.patch.object(trading_dates.aiomoex, "get_board_dates", return_value=JSON)

    loader = trading_dates.TradingDatesLoader()
    df = await loader.get(TABLE_NAME)
    await asyncio.sleep(0.01)

    pd.testing.assert_frame_equal(df, DF)
    outer_call.assert_called_once_with(
        resources.get_aiohttp_session(),
        board="TQBR",
        market="shares",
        engine="stock",
    )
    assert set(caplog.record_tuples) == {
        (LOGGER_CLASS_NAME, 20, "Загрузка TableName(group='trading_dates', name='trading_dates')"),
        (LOGGER_CLASS_NAME, 20, "Последняя дата с историей: 2020-09-22"),
    }


async def random_sleep(*args, **kwargs):
    """Эмитирует задержку загрузки данных."""
    await asyncio.sleep(random.random())  # noqa: S311
    return JSON


@pytest.mark.asyncio
async def test_get_many_times_with_cache(mocker, caplog):
    """Использования кэша после единственной загрузки."""
    caplog.set_level(logging.INFO)
    outer_call = mocker.patch.object(
        trading_dates.aiomoex,
        "get_board_dates",
        side_effect=random_sleep,
    )

    loader = trading_dates.TradingDatesLoader()
    aws = [loader.get(TABLE_NAME) for _ in range(100)]
    dfs = await asyncio.gather(*aws)

    outer_call.assert_called_once_with(
        resources.get_aiohttp_session(),
        board="TQBR",
        market="shares",
        engine="stock",
    )
    for df in dfs:
        pd.testing.assert_frame_equal(df, DF)

    assert set(caplog.record_tuples) == {
        (
            LOGGER_CLASS_NAME,
            20,
            "Загрузка из кэша TableName(group='trading_dates', name='trading_dates')",
        ),
        (LOGGER_CLASS_NAME, 20, "Загрузка TableName(group='trading_dates', name='trading_dates')"),
        (LOGGER_CLASS_NAME, 20, "Последняя дата с историей: 2020-09-22"),
    }
