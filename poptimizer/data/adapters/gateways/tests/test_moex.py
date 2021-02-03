"""Тесты загрузки данных с MOEX."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import moex
from poptimizer.shared import col


@pytest.mark.asyncio
async def test_trading_dates_gateway(mocker):
    """Загрузка данных о торговых днях."""
    json = [{"from": "1997-03-24", "till": "2020-09-22"}]
    outer_call = mocker.patch.object(moex.aiomoex, "get_board_dates", return_value=json)
    fake_session = mocker.Mock()

    gateway = moex.TradingDatesGateway(fake_session)
    df = await gateway.get()

    pd.testing.assert_frame_equal(df, pd.DataFrame(json, dtype="datetime64[ns]"))
    outer_call.assert_called_once_with(
        fake_session,
        board="TQBR",
        market="shares",
        engine="stock",
    )


@pytest.mark.asyncio
async def test_index_gateway(mocker):
    """Форматирование загруженных данных по индексу акциям."""
    df = pd.DataFrame([{"dd": "2020-09-29", "vv": 3000.0}])
    outer_call = mocker.patch.object(moex.aiomoex, "get_market_history", return_value=df)
    fake_session = mocker.Mock()

    loader = moex.IndexesGateway(fake_session)

    df_rez = await loader.get("INDEX", "start", "end")

    outer_call.assert_called_once_with(
        session=fake_session,
        start="start",
        end="end",
        security="INDEX",
        columns=("TRADEDATE", "CLOSE"),
        market="index",
    )

    assert df_rez.columns.tolist() == [col.CLOSE]
    assert df_rez.index.tolist() == [pd.Timestamp("2020-09-29")]
    assert df_rez.values.tolist() == [[3000.0]]


@pytest.mark.asyncio
async def test_securities_gateway(mocker):
    """Форматирование загруженных данных по торгуемым акциям."""
    df_rez = pd.DataFrame([{"ticker": "GAZP", "rn": "abc", "lot": 12}])
    outer_call = mocker.patch.object(moex.aiomoex, "get_board_securities", return_value=df_rez)
    fake_session = mocker.Mock()

    loader = moex.SecuritiesGateway(fake_session)

    df_rez = await loader.get("m1", "b1")

    assert df_rez.columns.tolist() == [col.ISIN, col.LOT_SIZE]
    assert df_rez.index.tolist() == ["GAZP"]
    assert df_rez.values.tolist() == [["abc", 12]]

    outer_call.assert_called_once_with(
        fake_session,
        market="m1",
        board="b1",
        columns=("SECID", "ISIN", "LOTSIZE"),
    )


@pytest.mark.asyncio
async def test_aliases_gateway(mocker):
    """Возврат данных в виде списка."""
    json = [
        {"secid": "OGKB", "isin": "1-02-65105-D"},
        {"secid": "OGK2", "isin": "1-02-65105-D"},
        {"secid": "OGK2-001D", "isin": "1-02-65105-D-001D"},
    ]
    outer_call = mocker.patch.object(moex.aiomoex, "find_securities", return_value=json)
    fake_session = mocker.Mock()

    loader = moex.AliasesGateway(fake_session)

    assert await loader.get("1-02-65105-D") == ["OGKB", "OGK2"]

    outer_call.assert_called_once_with(fake_session, "1-02-65105-D", columns=("secid", "isin"))


JSON = (
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
)


@pytest.mark.asyncio
async def test_quotes_gateway(mocker):
    """Загрузка данных с нужными столбцами."""
    outer_call = mocker.patch.object(moex.aiomoex, "get_market_candles", return_value=list(JSON))
    fake_session = mocker.Mock()

    loader = moex.QuotesGateway(fake_session)

    df_rez = await loader.get("TICKER", "m2", "start", "end")

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

    outer_call.assert_called_once_with(
        fake_session,
        "TICKER",
        market="m2",
        start="start",
        end="end",
    )


@pytest.mark.asyncio
async def test_quotes_gateway_regression_empty_json(mocker):
    """Регрессионный тест на загрузку пустого DataFrame с нужными столбцами.

    Очень специфическая ошибка для тикеров, которые торговались, потом сменили тикер и перестали
    торговаться - KSGR.
    """
    mocker.patch.object(moex.aiomoex, "get_market_candles", return_value=[])

    fake_session = mocker.Mock()

    loader = moex.QuotesGateway(fake_session)

    df_rez = await loader.get("TICKER", "m3", "start", "end")

    assert df_rez.empty
    assert df_rez.columns.tolist() == [
        col.OPEN,
        col.CLOSE,
        col.HIGH,
        col.LOW,
        col.TURNOVER,
    ]


@pytest.mark.asyncio
async def test_usd_gateway(mocker):
    """Загрузка данных с нужными столбцами."""
    fake_get_candles = mocker.patch.object(moex.aiomoex, "get_market_candles", return_value=list(JSON))
    fake_session = mocker.Mock()

    loader = moex.USDGateway(fake_session)

    df_rez = await loader.get("start", "end")

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

    fake_get_candles.assert_called_once_with(
        fake_session,
        "USD000UTSTOM",
        market="selt",
        engine="currency",
        start="start",
        end="end",
    )
