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
        events.TickerTraded("TICKER", "ISIN", "M1", date(2020, 12, 17), pd.DataFrame()),
        True,
    ),
    (
        pd.DataFrame(),
        events.UpdateDivCommand("TICKER"),
        True,
    ),
    (
        pd.DataFrame(),
        events.TickerTraded("TICKER", "ISIN", "M1", date(2020, 12, 17), pd.DataFrame()),
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
    """Корректно рассчитываются значения.

    Курс сдвигается вперед для отсутствующих дат.
    Рублевые значения не пересчитываются.
    Для задвоенных дат данные группируются и суммируются.
    """
    div_table._gateway = mocker.AsyncMock()
    div_table._gateway.return_value = pd.DataFrame(
        [
            [20, col.RUR],
            [30, col.USD],
            [40, col.USD],
            [10, col.RUR],
        ],
        index=[
            date(2020, 12, 16),
            date(2020, 12, 16),
            date(2021, 1, 11),
            date(2021, 2, 5),
        ],
        columns=["TICKER", col.CURRENCY],
    )

    usd = pd.DataFrame(
        [2, 3, 4],
        index=[
            date(2020, 12, 15),
            date(2021, 1, 10),
            date(2021, 2, 5),
        ],
        columns=[col.CLOSE],
    )
    event = events.TickerTraded("TICKER", "ISIN", "M1", date(2020, 12, 16), usd)

    pd.testing.assert_frame_equal(
        await div_table._prepare_df(event),
        pd.DataFrame(
            [80, 120, 10],
            index=[
                date(2020, 12, 16),
                date(2021, 1, 11),
                date(2021, 2, 5),
            ],
            columns=["TICKER"],
        ),
        check_dtype=False,
    )


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
    id_ = base.create_id(ports.DIV_NEW)
    return dividends.DivNew(id_)


def test_update_cond_smart_lab_table(smart_lab_table):
    """Всегда обновляется в конце рабочего дня."""
    assert smart_lab_table._update_cond(object())


@pytest.mark.asyncio
async def test_prepare_df_smart_lab_table(smart_lab_table, mocker):
    """Данные из нескольких шлюзов объединяются по оси х."""
    smart_lab_table._gateways = (
        mocker.AsyncMock(return_value=pd.DataFrame(index=["T-RM"])),
        mocker.AsyncMock(return_value=pd.DataFrame(index=["AKRN"])),
    )

    df = await smart_lab_table._prepare_df(object())
    assert df.index.tolist() == ["T-RM", "AKRN"]


def test_new_events_smart_lab_table(smart_lab_table):
    """Новые события не создаются."""
    smart_lab_table._df = pd.DataFrame(index=["AKRN", "AKRN", "CHMF"])
    new_events = smart_lab_table._new_events(object())

    assert isinstance(new_events, list)
    assert not new_events


@pytest.fixture(scope="function", name="div_ext_table")
def create_div_ext_table():
    """Создает пустую таблицу дивидендов внешних дивидендов для тестов."""
    id_ = base.create_id(ports.DIV_EXT)
    return dividends.DivExt(id_)


DIV_EXT_UPDATE_CASES = (
    (lambda: None, True),
    (lambda: datetime.utcnow() - timedelta(days=7, seconds=1), True),
    (lambda: datetime.utcnow() - timedelta(days=7, seconds=-1), False),
)


@pytest.mark.parametrize("timestamp_func, rez", DIV_EXT_UPDATE_CASES)
def test_update_cond_div_ext(div_ext_table, timestamp_func, rez):
    """Если дата обновления отсутствует или прошло 7 дней, то их надо загрузить."""
    div_ext_table._timestamp = timestamp_func()

    assert div_ext_table._update_cond(object()) is rez


@pytest.mark.asyncio
async def test_prepare_df_div_ext(div_ext_table, mocker):
    """Проверка агрегации данных."""
    event = events.UpdateDivCommand(
        ticker="GAZP",
        type_=col.ORDINARY,
        usd=pd.DataFrame(
            [2, 1],
            columns=[col.CLOSE],
            index=[datetime(2020, 12, 4), datetime(2020, 12, 5)],
        ),
    )
    fake_gateway = mocker.AsyncMock()
    fake_gateway.return_value = pd.DataFrame(
        [[3, col.RUR], [5, col.RUR]],
        columns=["GAZP", col.CURRENCY],
        index=[datetime(2020, 12, 4), datetime(2020, 12, 5)],
    )
    div_ext_table._gateways = (
        dividends.GateWayDesc("Dohod", col.ORDINARY, fake_gateway),
        dividends.GateWayDesc("NASDAQ", col.FOREIGN, fake_gateway),
    )

    df = await div_ext_table._prepare_df(event)

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [[3, 3], [5, 5]],
            columns=["Dohod", "MEDIAN"],
            index=[datetime(2020, 12, 4), datetime(2020, 12, 5)],
        ),
        check_dtype=False,
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
