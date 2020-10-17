"""Тестирование шины сообщений."""
from unittest import mock

import pytest

from poptimizer.data.app import event_bus
from poptimizer.data.domain import events

EVENT_CASES = (
    None,
    object(),
)


@pytest.mark.parametrize("table_name", EVENT_CASES)
@pytest.mark.asyncio
async def test_handle_one_command(mocker, table_name):
    """Обработка событий с загрузкой и без загрузки таблицы."""
    fake_event = mocker.AsyncMock()
    fake_event.table_required = table_name

    fake_repo = mocker.patch.object(event_bus.repo, "Repo").return_value
    fake_repo = fake_repo.__aenter__.return_value  # noqa: WPS609

    bus = event_bus.EventBus(mocker.sentinel)
    new_event = await bus._handle_one_command(fake_event)

    table = None
    if table_name is not None:
        table = fake_repo.get_table.return_value

    fake_event.handle_event.assert_called_once_with(table)
    assert new_event is fake_event.handle_event.return_value


@pytest.mark.asyncio
async def test_event_bus_create_task(mocker):
    """Метод создания задач возвращает корректно созданное задание по обработке события."""
    fake_event = mocker.sentinel
    fake_task = mocker.patch.object(event_bus.asyncio, "create_task").return_value

    bus = event_bus.EventBus(mocker.sentinel)
    fake_handle_one_command = mocker.patch.object(bus, "_handle_one_command")

    assert bus._create_task(fake_event) is fake_task
    fake_handle_one_command.assert_called_once_with(fake_event)


RESULT_MOCK = mock.Mock()
RESULT_MOCK.__class__ = events.Result
COMMAND_MOCK = mock.Mock()
COMMAND_MOCK.__class__ = events.Command

RESULT_CASE = (
    (RESULT_MOCK, True),
    (COMMAND_MOCK, False),
)


@pytest.mark.parametrize("event, check_rez", RESULT_CASE)
@pytest.mark.asyncio
async def test_gather_results(event, check_rez):
    """Обработка сбора результатов."""
    events_results = {}
    event_bus._gather_results(events_results, event)

    if check_rez:
        assert len(events_results) == 1
        assert events_results == {event.name: event.df}
    else:
        assert not events_results


COMMAND_CASE = (
    (RESULT_MOCK, False),
    (COMMAND_MOCK, True),
)


@pytest.mark.parametrize("event, check_com", COMMAND_CASE)
@pytest.mark.asyncio
async def test_add_pending(mocker, event, check_com):
    """Обработка добавления нового задания."""
    bus = event_bus.EventBus(mocker.sentinel)
    fake_create_task = mocker.patch.object(bus, "_create_task")

    pending = set()
    bus._add_pending(pending, event)

    if check_com:
        fake_create_task.assert_called_once_with(event)
        assert len(pending) == 1
        assert pending == {fake_create_task.return_value}
    else:
        assert not pending
