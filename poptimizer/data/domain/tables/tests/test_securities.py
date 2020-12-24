"""Тесты для таблицы с торгуемыми ценными бумагами."""
from datetime import date

import pandas as pd
import pytest

from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base, securities
from poptimizer.shared import col


@pytest.fixture(scope="function", name="table")
def create_table():
    """Создает пустую таблицу для тестов."""
    id_ = base.create_id(ports.SECURITIES)
    return securities.Securities(id_)


def test_update_cond(table):
    """Обновление происходит всегда при поступлении события."""
    assert table._update_cond(object())


@pytest.mark.asyncio
async def test_load_and_format_df(table, mocker):
    """Данные загружаются и добавляется колонка с названием рынка."""
    fake_gateway = mocker.AsyncMock()
    fake_gateway.get.return_value = pd.DataFrame([1, 2])
    table._gateway = fake_gateway

    df = await table._load_and_format_df("m1", "b1")

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame([[1, "m1"], [2, "m1"]], columns=[0, col.MARKET]),
    )
    fake_gateway.get.assert_called_once_with(market="m1", board="b1")


@pytest.mark.asyncio
async def test_prepare_df(table, mocker):
    """Данные загружаются объединяются и сортируются."""
    dfs = [
        pd.DataFrame([1], index=[2]),
        pd.DataFrame([2], index=[3]),
        pd.DataFrame([3], index=[1]),
    ]
    fake_gateway = mocker.AsyncMock()
    fake_gateway.get.side_effect = dfs
    table._gateway = fake_gateway

    df = await table._prepare_df(object())

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [[3, "foreignshares"], [1, "shares"], [2, "shares"]],
            index=[1, 2, 3],
            columns=[0, col.MARKET],
        ),
    )


def test_validate_new_df(mocker, table):
    """Осуществляется проверка на уникальность и возрастание индекса."""
    mocker.patch.object(base, "check_unique_increasing_index")

    table._validate_new_df(mocker.sentinel)

    base.check_unique_increasing_index.assert_called_once_with(mocker.sentinel)


def test_new_events(table):
    """Создание событий для всех торгуемых тикеров."""
    table._df = pd.DataFrame(
        [["YY", 10, "m2"], ["UU", 100, "m1"]],
        columns=[col.ISIN, col.LOT_SIZE, col.MARKET],
        index=["GAZP", "AKRN"],
    )
    trading_date = date(2020, 12, 15)
    event = events.TradingDayEnded(trading_date)

    assert table._new_events(event) == [
        events.TickerTraded("GAZP", "YY", "m2", trading_date),
        events.TickerTraded("AKRN", "UU", "m1", trading_date),
    ]
