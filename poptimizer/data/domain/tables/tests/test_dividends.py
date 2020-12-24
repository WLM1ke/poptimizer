"""Тесты для таблиц с дивидендами."""
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base, dividends
from poptimizer.shared import col


@pytest.fixture(scope="function", name="div_table")
def create_div_table():
    """Создает пустую таблицу дивидендов для тестов."""
    id_ = base.create_id(ports.DIVIDENDS)
    return dividends.Dividends(id_)


DIV_UPDATE_CASES = (
    (
        None,
        events.TickerTraded("TICKER", "ISIN", "M1", date(2020, 12, 17)),
        True,
    ),
    (
        pd.DataFrame(),
        events.UpdateDivCommand("TICKER"),
        True,
    ),
    (
        pd.DataFrame(),
        events.TickerTraded("TICKER", "ISIN", "M1", date(2020, 12, 17)),
        False,
    ),
)


@pytest.mark.parametrize("df, event, rez", DIV_UPDATE_CASES)
def test_update_cond(div_table, df, event, rez):
    """Если дивиденды отсутствуют и поступила команда обновления, то их надо загрузить."""
    div_table._df = df

    assert div_table._update_cond(event) is rez


@pytest.mark.asyncio
async def test_prepare_df(div_table, mocker):
    """Данные загружаются для тикера из события."""
    div_table._gateway = mocker.AsyncMock()

    event = events.TickerTraded("TICKER", "ISIN", "M1", date(2020, 12, 17))

    fake_get = div_table._gateway.get
    assert await div_table._prepare_df(event) is fake_get.return_value
    fake_get.assert_called_once_with("TICKER")


def test_validate_new_df(mocker, div_table):
    """Осуществляется проверка на уникальность и возрастание индекса."""
    mocker.patch.object(base, "check_unique_increasing_index")

    div_table._validate_new_df(mocker.sentinel)

    base.check_unique_increasing_index.assert_called_once_with(mocker.sentinel)


def test_new_events(div_table):
    """Новые события не порождаются."""
    new_events = div_table._new_events(object())
    assert isinstance(new_events, list)
    assert not new_events


@pytest.fixture(scope="function", name="smart_lab_table")
def create_smart_lab_table():
    """Создает пустую таблицу дивидендов со SmartLab для тестов."""
    id_ = base.create_id(ports.SMART_LAB)
    return dividends.SmartLab(id_)


def test_update_cond_smart_lab_table(smart_lab_table):
    """Всегда обновляется в конце рабочего дня."""
    assert smart_lab_table._update_cond(object())


@pytest.mark.asyncio
async def test_prepare_df_smart_lab_table(smart_lab_table, mocker):
    """Данные загружаются с помощью шлюза."""
    smart_lab_table._gateway = mocker.AsyncMock()

    fake_get = smart_lab_table._gateway.get
    assert await smart_lab_table._prepare_df(object()) is fake_get.return_value
    fake_get.assert_called_once_with()


def test_new_events_smart_lab_table(smart_lab_table):
    """Создаются события для каждого тикера со сводной информацией о дивидендах."""
    smart_lab_table._df = pd.DataFrame(
        [
            [datetime(2020, 12, 1), 3],
            [datetime(2020, 12, 2), 2],
            [datetime(2020, 12, 3), 1],
        ],
        index=["AKRN", "CHMF", "CHMF"],
        columns=[col.DATE, col.DIVIDENDS],
    )

    new_events = smart_lab_table._new_events(object())

    assert isinstance(new_events, list)
    assert len(new_events) == 2

    answers = {
        "AKRN": pd.DataFrame(
            [3],
            columns=["SmartLab"],
            index=[datetime(2020, 12, 1)],
        ),
        "CHMF": pd.DataFrame(
            [2, 1],
            columns=["SmartLab"],
            index=[datetime(2020, 12, 2), datetime(2020, 12, 3)],
        ),
    }

    for new_event in new_events:
        assert isinstance(new_event, events.DivExpected)
        ticker = new_event.ticker
        pd.testing.assert_frame_equal(
            new_event.df,
            answers[ticker],
            check_names=False,
        )


@pytest.fixture(scope="function", name="div_ext_table")
def create_div_ext_table():
    """Создает пустую таблицу дивидендов внешних дивидендов для тестов."""
    id_ = base.create_id(ports.DIV_EXT)
    return dividends.DivExt(id_)


DIV_EXT_UPDATE_CASES = (
    (None, True),
    (datetime.utcnow() - timedelta(days=7, seconds=1), True),
    (datetime.utcnow() - timedelta(days=7, seconds=-1), False),
)


@pytest.mark.parametrize("timestamp, rez", DIV_EXT_UPDATE_CASES)
def test_update_cond_div_ext(div_ext_table, timestamp, rez):
    """Если дата обновления отсутствует или прошло 7 дней, то их надо загрузить."""
    div_ext_table._timestamp = timestamp

    assert div_ext_table._update_cond(object()) is rez


@pytest.mark.asyncio
async def test_prepare_df_div_ext(div_ext_table, mocker):
    """Проверка агрегации данных."""
    event = events.DivExpected(
        ticker="GAZP",
        df=pd.DataFrame(
            [2, 1],
            columns=["SmartLab"],
            index=[datetime(2020, 12, 4), datetime(2020, 12, 5)],
        ),
    )
    fake_gateway = mocker.AsyncMock()
    fake_gateway.get.return_value = pd.DataFrame(
        [3, 5],
        columns=["GAZP"],
        index=[datetime(2020, 12, 4), datetime(2020, 12, 5)],
    )
    div_ext_table._gateways_dict = {"S1": fake_gateway}

    df = await div_ext_table._prepare_df(event)

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [[2, 3, 2.5], [1, 5, 3.0]],
            columns=["SmartLab", "S1", "MEDIAN"],
            index=[datetime(2020, 12, 4), datetime(2020, 12, 5)],
        ),
    )


def test_validate_div_ext(mocker, div_ext_table):
    """Осуществляется проверка на уникальность и возрастание индекса."""
    mocker.patch.object(base, "check_unique_increasing_index")

    div_ext_table._validate_new_df(mocker.sentinel)

    base.check_unique_increasing_index.assert_called_once_with(mocker.sentinel)


def test_new_events_div_ext(div_ext_table):
    """Новые события не порождаются."""
    new_events = div_ext_table._new_events(object())
    assert isinstance(new_events, list)
    assert not new_events
