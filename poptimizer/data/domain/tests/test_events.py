"""Тесты событий, связанных с обновлением таблиц."""
import asyncio
from datetime import datetime

import pytest

from poptimizer.data.domain import events, services
from poptimizer.data.ports import outer

HELPER_NAME = outer.TableName(outer.TRADING_DATES, outer.TRADING_DATES)
USUAL_NAME = outer.TableName(outer.QUOTES, "SNGSP")
FAKE_END_OF_TRADING_DAY = datetime(2020, 9, 15, 15, 58)


GET_DATA_FRAME_CASES = (
    (
        (USUAL_NAME, True),
        events.UpdateWithTimestampRequired,
        USUAL_NAME,
        "_end_of_trading_day",
        None,
    ),
    (
        (USUAL_NAME, False),
        events.UpdateWithHelperRequired,
        HELPER_NAME,
        "_table_name",
        USUAL_NAME,
    ),
    (
        (HELPER_NAME, False),
        events.UpdateWithTimestampRequired,
        HELPER_NAME,
        "_end_of_trading_day",
        services._trading_day_potential_end(),
    ),
)


@pytest.mark.parametrize(
    "event_args, child_type, child_name, child_attr, child_value",
    GET_DATA_FRAME_CASES,
)
@pytest.mark.asyncio
async def test_get_data_frame(
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

    event = events.UpdatedDfRequired(*event_args)
    assert event.table_required is None

    await event.handle_event(queue, None)
    assert queue.qsize() == 1

    child_event = await queue.get()
    assert isinstance(child_event, child_type)
    assert child_event.table_required == child_name
    assert getattr(child_event, child_attr) == child_value


@pytest.mark.asyncio
async def test_end_of_trading_day(monkeypatch, mocker):
    """Обновляет вспомогательную таблицу и не добавляет новые событие по обновлению основной таблицы."""
    monkeypatch.setattr(services, "trading_day_real_end", lambda _: FAKE_END_OF_TRADING_DAY)
    mocker_table = mocker.AsyncMock()
    queue = asyncio.Queue()

    event = events.UpdateWithHelperRequired(USUAL_NAME, HELPER_NAME)
    assert event.table_required is HELPER_NAME

    await event.handle_event(queue, mocker_table)
    assert queue.qsize() == 1
    mocker_table.update.assert_called_once_with(services._trading_day_potential_end())

    child_event = await queue.get()
    assert isinstance(child_event, events.UpdateWithTimestampRequired)
    assert child_event.table_required == USUAL_NAME

    assert child_event._end_of_trading_day == FAKE_END_OF_TRADING_DAY


@pytest.mark.asyncio
async def test_end_of_trading_day_raises():
    """Исключение при попытке обработки без таблицы."""
    queue = asyncio.Queue()

    event = events.UpdateWithHelperRequired(USUAL_NAME, HELPER_NAME)
    with pytest.raises(outer.DataError, match="Нужна таблица"):
        await event.handle_event(queue, None)


@pytest.mark.asyncio
async def test_update_table(mocker):
    """Обновляет таблицу и не добавляет новые события."""
    mocker_table = mocker.AsyncMock()
    queue = asyncio.Queue()

    event = events.UpdateWithTimestampRequired(USUAL_NAME, FAKE_END_OF_TRADING_DAY)
    assert event.table_required is USUAL_NAME

    await event.handle_event(queue, mocker_table)
    assert queue.qsize() == 1
    mocker_table.update.assert_called_once_with(FAKE_END_OF_TRADING_DAY)

    child_event = await queue.get()
    assert isinstance(child_event, events.Result)
    assert child_event.name is mocker_table.name
    assert child_event.df is mocker_table.df


@pytest.mark.asyncio
async def test_update_table_raises():
    """Исключение при попытке обработки без таблицы."""
    queue = asyncio.Queue()

    event = events.UpdateWithTimestampRequired(USUAL_NAME, FAKE_END_OF_TRADING_DAY)
    with pytest.raises(outer.DataError, match="Нужна таблица"):
        await event.handle_event(queue, None)
