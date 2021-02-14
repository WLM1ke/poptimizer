"""Тесты обновления таблицы с торговыми датами."""
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base, trading_dates

UTC_NAIVE_CASES = (
    (
        datetime(2020, 12, 14, 13, 54, tzinfo=timezone(timedelta(hours=3))),
        datetime(2020, 12, 14, 10, 54),
    ),
    (
        datetime(2020, 12, 14, 13, 54, tzinfo=timezone(timedelta(hours=0))),
        datetime(2020, 12, 14, 13, 54),
    ),
)


@pytest.mark.parametrize("timestamp, rez", UTC_NAIVE_CASES)
def test_to_utc_naive(timestamp, rez):
    """Проверка преобразования времени и отбрасывания зоны."""
    assert trading_dates._to_utc_naive(timestamp) == rez


class FakeDateTime:
    """Возвращает текущее время в регионе биржи."""

    def __init__(self, timestamp):
        """Сохраняет условное текущее время."""
        self.date = timestamp

    def now(self, tzinfo):
        """Патч для текущего времени с указанной зоной."""
        return self.date.replace(tzinfo=tzinfo)


TRADING_DAY_POTENTIAL_END_CASES = (
    (
        datetime(2020, 9, 12, 0, 46),
        datetime(2020, 9, 11, 21, 45),
    ),
    (
        datetime(2020, 9, 12, 0, 44),
        datetime(2020, 9, 10, 21, 45),
    ),
)


@pytest.mark.parametrize("now, end", TRADING_DAY_POTENTIAL_END_CASES)
def test_trading_day_potential_end(now, end, monkeypatch):
    """Тестирование двух краевых случаев на стыке потенциального окончания торгового дня."""
    monkeypatch.setattr(trading_dates, "datetime", FakeDateTime(now))
    assert trading_dates._trading_day_potential_end() == end


@pytest.fixture(scope="function", name="table")
def make_table():
    """Создает пустую таблицу."""
    id_ = base.create_id(ports.TRADING_DATES)
    return trading_dates.TradingDates(id_)


UPDATE_COND_CASES = (
    (
        None,
        datetime(2020, 12, 14, 14, 4),
        True,
    ),
    (
        datetime(2020, 12, 14, 14, 3),
        datetime(2020, 12, 14, 14, 4),
        True,
    ),
    (
        datetime(2020, 12, 14, 14, 4),
        datetime(2020, 12, 14, 14, 4),
        False,
    ),
)


@pytest.mark.parametrize("timestamp, trading_end, rez", UPDATE_COND_CASES)
def test_update_cond(table, timestamp, trading_end, rez, mocker):
    """Проверка трех вариантов обновления."""
    table._timestamp = timestamp
    mocker.patch.object(trading_dates, "_trading_day_potential_end", return_value=trading_end)

    assert table._update_cond("") is rez


@pytest.mark.asyncio
async def test_prepare_df(table, mocker):
    """Вызов по подготовке DataFrame переадресуется шлюзу."""
    fake_gateway = mocker.AsyncMock()
    table._gateway = fake_gateway

    assert await table._prepare_df("") == fake_gateway.return_value


VALIDATE_CASES = (
    (
        None,
        pd.DataFrame(index=[1]),
        True,
    ),
    (
        None,
        pd.DataFrame(index=[0], columns=["from", "t"]),
        True,
    ),
    (
        pd.DataFrame("test", index=[0], columns=["till"]),
        pd.DataFrame(index=[0], columns=["from", "till"]),
        False,
    ),
    (
        None,
        pd.DataFrame(index=[0], columns=["from", "till"]),
        None,
    ),
)


@pytest.mark.parametrize("df_old, df_new, raises", VALIDATE_CASES)
def test_validate_new_df(table, df_old, df_new, raises):
    """Выполняет проверки и сохраняет старое значение даты."""
    table._df = df_old

    if raises:
        with pytest.raises(base.TableIndexError):
            table._validate_new_df(df_new)
    elif raises is False:
        table._validate_new_df(df_new)
        assert table._last_trading_day_old == "test"
    else:
        table._validate_new_df(df_new)
        assert table._last_trading_day_old is None


NEW_EVENTS_CASES = (
    (
        pd.DataFrame(datetime(2020, 12, 14), index=[0], columns=["till"]),
        datetime(2020, 12, 14),
        [],
    ),
    (
        pd.DataFrame(datetime(2020, 12, 14), index=[0], columns=["till"]),
        datetime(2020, 12, 13),
        [events.TradingDayEnded(date(2020, 12, 14))],
    ),
)


@pytest.mark.parametrize("df, old_date, new_events", NEW_EVENTS_CASES)
def test_new_events(table, df, old_date, new_events):
    """Два результата в зависимости от изменения даты."""
    table._df = df
    table._last_trading_day_old = old_date

    assert table._new_events("") == new_events
