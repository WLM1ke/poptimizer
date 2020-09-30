"""Тестирование шины сообщений."""
from unittest import mock

import pytest

from poptimizer.data.app import event_bus
from poptimizer.data.domain import events
from poptimizer.data.ports import outer

EVENT_CASES = (
    None,
    object(),
)


@pytest.mark.parametrize("table_name", EVENT_CASES)
@pytest.mark.asyncio
async def test_handle_one_command(mocker, table_name):
    """Обработка событий с загрузкой и без загрузки таблицы."""
    fake_db_session = mocker.sentinel
    fake_queue = mocker.Mock()
    fake_event = mocker.AsyncMock()
    fake_event.table_required = table_name

    fake_repo = mocker.patch.object(event_bus.repo, "Repo").return_value
    fake_repo = fake_repo.__aenter__.return_value  # noqa: WPS609

    await event_bus._handle_one_command(fake_db_session, fake_queue, fake_event)

    table = None
    if table_name is not None:
        table = fake_repo.get_table.return_value

    fake_event.handle_event.assert_called_once_with(fake_queue, table)
    fake_queue.task_done.assert_called_once_with()


RESULT_MOCK = mock.Mock()
RESULT_MOCK.__class__ = events.Result
COMMAND_MOCK = mock.Mock()
COMMAND_MOCK.__class__ = events.Command

TYPE_CASE = (
    (RESULT_MOCK, True, False),
    (COMMAND_MOCK, False, False),
    (object(), False, True),
)


@pytest.mark.parametrize("event, check_rez, raises", TYPE_CASE)
@pytest.mark.asyncio
async def test_dispatch_event(mocker, event, check_rez, raises):
    """Обработка двух типов событий и выбрасование исключения на непонятном событии."""
    fake_db_session = mocker.sentinel
    fake_queue = mocker.AsyncMock()
    fake_queue.get.return_value = event

    if raises:
        with pytest.raises(outer.DataError, match="Неизвестный тип события"):
            await event_bus._dispatch_event(fake_db_session, fake_queue)
        return

    rez = await event_bus._dispatch_event(fake_db_session, fake_queue)

    fake_queue.get.assert_called_once_with()
    if check_rez:
        fake_queue.task_done.assert_called_once_with()
        assert rez == (event.name, event.df)
    else:
        assert rez is None


@pytest.mark.asyncio
async def test_queue_processor(mocker):
    """Процессор дожидается получения нужного количества результатов."""
    fake_db_session = mocker.sentinel
    fake_queue = mocker.Mock()
    fake_queue.qsize.return_value = 2

    side_effect = [None, ("a", "b"), None, ("c", "d")]
    mocker.patch.object(event_bus, "_dispatch_event", side_effect=side_effect)

    assert await event_bus._queue_processor(fake_db_session, fake_queue) == {"a": "b", "c": "d"}


@pytest.mark.asyncio
async def test_event_bus(mocker):
    """Обработчик кладет все задания в очередь, завершает ее работу и возвращает результат задания."""
    fake_db_session = mocker.sentinel
    fake_queue = mocker.patch.object(
        event_bus.asyncio,
        "Queue",
        return_value=mocker.AsyncMock(),
    ).return_value
    fake_task = mocker.patch.object(event_bus.asyncio, "create_task").return_value

    bus = event_bus.EventBus(fake_db_session)
    assert await bus.handle_events(list(range(5))) == fake_task.result.return_value

    assert fake_queue.put.call_count == 5
    fake_queue.join.assert_called_once_with()
