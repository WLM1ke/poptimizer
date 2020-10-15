"""Тесты для загрузки данных с MOEX."""
import asyncio
import logging
from datetime import datetime

import pandas as pd
import pytest

from poptimizer.data.adapters.loaders import moex
from poptimizer.data.config import resources
from poptimizer.data.ports import col, outer

# flake8: noqa

NAMES_CASES = (
    (moex.SecuritiesLoader(), outer.TableName(outer.SECURITIES, "test")),
    (moex.SecuritiesLoader(), outer.TableName(outer.QUOTES, outer.SECURITIES)),
    (moex.IndexLoader(), outer.TableName(outer.INDEX, "test")),
    (moex.IndexLoader(), outer.TableName(outer.QUOTES, outer.INDEX)),
    (moex.QuotesLoader(moex.SecuritiesLoader()), outer.TableName(outer.SECURITIES, "AKRN")),
)


@pytest.mark.parametrize("loader, table_name", NAMES_CASES)
@pytest.mark.asyncio
async def test_loader_raise_on_wrong_name(loader, table_name):
    """Не верное название таблицы."""
    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        await loader.get(table_name)


DF_SEC = pd.DataFrame([dict(ticker="GAZP", rn="abc", lot=12)])


@pytest.mark.asyncio
async def test_securities_loader(mocker):
    """Форматирование загруженных данных по торгуемым акциям."""
    mocker.patch.object(moex.aiomoex, "get_board_securities", return_value=DF_SEC)

    loader = moex.SecuritiesLoader()
    table_name = outer.TableName(outer.SECURITIES, outer.SECURITIES)

    df_rez = await loader.get(table_name)

    assert df_rez.columns.tolist() == [col.ISIN, col.LOT_SIZE]
    assert df_rez.index.tolist() == ["GAZP"]
    assert df_rez.values.tolist() == [["abc", 12]]


@pytest.mark.asyncio
async def test_securities_loader_from_cache(mocker, caplog):
    """Проверка повторной загрузки из кэша."""
    caplog.set_level(logging.INFO)
    fake_get_board_securities = mocker.patch.object(
        moex.aiomoex,
        "get_board_securities",
        return_value=DF_SEC,
    )

    loader = moex.SecuritiesLoader()
    table_name = outer.TableName(outer.SECURITIES, outer.SECURITIES)

    df_rez1 = await loader.get(table_name)
    fake_get_board_securities.assert_called_once()

    await asyncio.sleep(0.01)
    assert len(caplog.record_tuples) == 1
    assert "Загрузка из кэша" not in caplog.record_tuples[0][-1]

    df_rez2 = await loader.get(table_name)

    fake_get_board_securities.assert_called_once()
    pd.testing.assert_frame_equal(df_rez1, df_rez2)
    await asyncio.sleep(0.01)
    assert len(caplog.record_tuples) == 3
    assert "Загрузка из кэша" in caplog.record_tuples[2][-1]


@pytest.mark.asyncio
async def test_index_loader(mocker):
    """Форматирование загруженных данных по индексу акциям."""
    df = pd.DataFrame([dict(dd="2020-09-29", vv=3000.0)])
    mocker.patch.object(moex.aiomoex, "get_board_history", return_value=df)

    loader = moex.IndexLoader()
    table_name = outer.TableName(outer.INDEX, outer.INDEX)

    df_rez = await loader.get(table_name)

    assert df_rez.columns.tolist() == [col.CLOSE]
    assert df_rez.index.tolist() == [pd.Timestamp("2020-09-29")]
    assert df_rez.values.tolist() == [[3000.0]]


def test_previous_day_in_moscow(mocker):
    """Определение предыдущего дня."""
    fake_datetime = mocker.patch.object(moex, "datetime")
    fake_datetime.now.return_value = datetime(2020, 9, 30, 12, 56)
    assert moex._previous_day_in_moscow() == "2020-09-29"
    fake_datetime.now.assert_called_once_with(moex.MOEX_TZ)


@pytest.mark.asyncio
async def test_find_aliases(mocker):
    """Загрузка альтернативных тикеров в виде массива."""
    json = [
        {"secid": "OGKB", "isin": "1-02-65105-D"},
        {"secid": "OGK2", "isin": "1-02-65105-D"},
        {"secid": "OGK2-001D", "isin": "1-02-65105-D-001D"},
    ]
    mocker.patch.object(moex.aiomoex, "find_securities", return_value=json)
    session = resources.get_aiohttp_session()
    assert await moex._find_aliases(session, "1-02-65105-D") == ["OGKB", "OGK2"]


JSON1 = [
    {
        "open": 1,
        "close": 2,
        "high": 3,
        "low": 4,
        "value": 5,
        "volume": 6,
        "begin": "2011-09-27 00:00:00",
        "end": "2011-09-27 23:59:59",
    },
    {
        "open": 7,
        "close": 9,
        "high": 9,
        "low": 10,
        "value": 11,
        "volume": 12,
        "begin": "2011-09-28 00:00:00",
        "end": "2011-09-28 23:59:59",
    },
]
JSON2 = [
    {
        "open": 1,
        "close": 3,
        "high": 3,
        "low": 4,
        "value": 5,
        "volume": 6,
        "begin": "2011-09-29 00:00:00",
        "end": "2011-09-29 23:59:59",
    },
    {
        "open": 7,
        "close": 8,
        "high": 9,
        "low": 10,
        "value": 11,
        "volume": 19,
        "begin": "2011-09-28 00:00:00",
        "end": "2011-09-28 23:59:59",
    },
]


@pytest.mark.asyncio
async def test_download_many(mocker):
    """Загрузка многих и выбор с максимального оборота для дублирующихся дат."""
    mocker.patch.object(moex.aiomoex, "get_market_candles", side_effect=[JSON1, JSON2])
    session = resources.get_aiohttp_session()
    df = await moex._download_many(session, ["OGKB3", "OGK4"])
    assert df.columns.tolist() == [
        "begin",
        "open",
        "close",
        "high",
        "low",
        "value",
        "volume",
        "end",
    ]
    assert df["begin"].tolist() == [
        "2011-09-27 00:00:00",
        "2011-09-28 00:00:00",
        "2011-09-29 00:00:00",
    ]
    assert df["close"].tolist() == [
        2,
        8,
        3,
    ]


@pytest.mark.asyncio
async def test_download_many_empty(mocker):
    """Корректное наименование столбцов при отсутствии данных."""
    mocker.patch.object(moex.aiomoex, "get_market_candles", side_effect=[[], []])
    session = resources.get_aiohttp_session()
    df = await moex._download_many(session, ["OGKB", "OGK2"])
    assert df.empty
    assert df.columns.tolist() == ["begin", "open", "close", "high", "low", "value"]


@pytest.mark.asyncio
async def test_loader_first_load(mocker):
    """Вариант загрузки без начальной датой."""
    fake_securities_loader = mocker.AsyncMock()
    mocker.patch.object(moex, "_find_aliases", return_value=["a", "b"])
    mocker.patch.object(moex.aiomoex, "get_market_candles", side_effect=[JSON1, JSON2])

    loader = moex.QuotesLoader(fake_securities_loader)
    table_name = outer.TableName(outer.QUOTES, "AKRN")
    df_rez = await loader.get(table_name)

    assert df_rez.columns.tolist() == [
        col.OPEN,
        col.CLOSE,
        col.HIGH,
        col.LOW,
        col.TURNOVER,
    ]
    assert df_rez.index.tolist() == [
        pd.Timestamp("2011-09-27"),
        pd.Timestamp("2011-09-28"),
        pd.Timestamp("2011-09-29"),
    ]
    assert df_rez[col.CLOSE].tolist() == [
        2,
        8,
        3,
    ]


@pytest.mark.asyncio
async def test_loader_not_first_load(mocker):
    """Вариант загрузки с начальной датой."""
    fake_securities_loader = mocker.AsyncMock()
    mocker.patch.object(moex.aiomoex, "get_market_candles", return_value=JSON1)

    loader = moex.QuotesLoader(fake_securities_loader)
    table_name = outer.TableName(outer.QUOTES, "AKRN")
    df_rez = await loader.get(table_name, "2011-09-28")

    assert df_rez.columns.tolist() == [
        col.OPEN,
        col.CLOSE,
        col.HIGH,
        col.LOW,
        col.TURNOVER,
    ]
    assert df_rez.index.tolist() == [
        pd.Timestamp("2011-09-27"),
        pd.Timestamp("2011-09-28"),
    ]
    assert df_rez[col.CLOSE].tolist() == [
        2,
        9,
    ]


@pytest.mark.asyncio
async def test_regression_loader_not_first_load_empty(mocker):
    """Регрессионный тест на загрузку пустого DataFrame с нужными столбцами.

    Очень специфическая ошибка для тикеров, которые торговались, потом сменили тикер и перестали
    торговаться - KSGR.
    """
    fake_securities_loader = mocker.AsyncMock()
    mocker.patch.object(moex.aiomoex, "get_market_candles", return_value=[])

    loader = moex.QuotesLoader(fake_securities_loader)
    table_name = outer.TableName(outer.QUOTES, "AKRN")
    df_rez = await loader.get(table_name, "2011-09-28")

    assert df_rez.empty
    assert df_rez.columns.tolist() == [
        col.OPEN,
        col.CLOSE,
        col.HIGH,
        col.LOW,
        col.TURNOVER,
    ]
