"""Тесты событий, связанных с обновлением таблиц."""
import asyncio
from datetime import datetime

import pytest

from poptimizer.data.domain import events, services
from poptimizer.data.ports import base

HELPER_NAME = base.TableName(base.TRADING_DATES, base.TRADING_DATES)
USUAL_NAME = base.TableName(base.QUOTES, "SNGSP")
FAKE_END_OF_TRADING_DAY = datetime(2020, 9, 15, 15, 58)


UPDATE_CHECKED_CASES = (
    (
        (USUAL_NAME, True),
        events.TradingDateLoaded,
        USUAL_NAME,
        "_end_of_trading_day",
        None,
    ),
    (
        (USUAL_NAME, False),
        events.TradingDayEndRequired,
        HELPER_NAME,
        "_table_name",
        USUAL_NAME,
    ),
    (
        (HELPER_NAME, False),
        events.TradingDateLoaded,
        HELPER_NAME,
        "_end_of_trading_day",
        services.trading_day_potential_end(),
    ),
)


@pytest.mark.parametrize(
    "event_args, child_type, child_name, child_attr, child_value",
    UPDATE_CHECKED_CASES,
)
@pytest.mark.asyncio
async def test_update_checked_force(
    event_args,
    child_type,
    child_name,
    child_attr,
    child_value,
):
    """Проверяет три основных сценария.

    - принудительное обновление
    - обновление с помощью вспомогательной таблицы
    - обновление без вспомогательной таблицы
    """
    queue = asyncio.Queue()

    event = events.UpdateChecked(*event_args)
    assert event.table_required is None

    await event.handle_event(queue, None)
    assert queue.qsize() == 1

    child_event = await queue.get()
    assert isinstance(child_event, child_type)
    assert child_event.table_required == child_name
    assert getattr(child_event, child_attr) == child_value


@pytest.mark.asyncio
async def test_trading_day_required(monkeypatch, mocker):
    """Обновляет вспомогательную таблицу и не добавляет новые событие по обновлению основной таблицы."""
    monkeypatch.setattr(services, "trading_day_real_end", lambda _: FAKE_END_OF_TRADING_DAY)
    mocker_table = mocker.AsyncMock()
    queue = asyncio.Queue()

    event = events.TradingDayEndRequired(USUAL_NAME, HELPER_NAME)
    assert event.table_required is HELPER_NAME

    await event.handle_event(queue, mocker_table)
    assert queue.qsize() == 1
    mocker_table.update.assert_called_once_with(services.trading_day_potential_end())

    child_event = await queue.get()
    assert isinstance(child_event, events.TradingDateLoaded)
    assert child_event.table_required == USUAL_NAME

    assert child_event._end_of_trading_day == FAKE_END_OF_TRADING_DAY


@pytest.mark.asyncio
async def test_trading_day_required_raises():
    """Исключение при попытке обработки без таблицы."""
    queue = asyncio.Queue()

    event = events.TradingDayEndRequired(USUAL_NAME, HELPER_NAME)
    with pytest.raises(base.DataError, match="Нужна таблица"):
        await event.handle_event(queue, None)


@pytest.mark.asyncio
async def test_trading_day_loaded(mocker):
    """Обновляет таблицу и не добавляет новые события."""
    mocker_table = mocker.AsyncMock()
    queue = asyncio.Queue()

    event = events.TradingDateLoaded(USUAL_NAME, FAKE_END_OF_TRADING_DAY)
    assert event.table_required is USUAL_NAME

    await event.handle_event(queue, mocker_table)
    assert queue.qsize() == 0
    mocker_table.update.assert_called_once_with(FAKE_END_OF_TRADING_DAY)


@pytest.mark.asyncio
async def test_trading_day_loaded_raises():
    """Исключение при попытке обработки без таблицы."""
    queue = asyncio.Queue()

    event = events.TradingDateLoaded(USUAL_NAME, FAKE_END_OF_TRADING_DAY)
    with pytest.raises(base.DataError, match="Нужна таблица"):
        await event.handle_event(queue, None)
