"""Тесты для общих классов слоя приложения."""
import pytest

from poptimizer.data_di.shared import app


@pytest.mark.asyncio
async def test_uow_ctx_repo(mocker):
    """Проверка, что в контексте UoW сохраняются загруженные объекты."""
    fake_mapper = mocker.AsyncMock()
    fake_mapper.get.side_effect = ["first_rez", "second_rez"]
    fake_commit = fake_mapper.commit

    async with app.UoW(fake_mapper) as repo:
        assert await repo.get("first") == "first_rez"
        assert await repo.get("second") == "second_rez"

    assert fake_commit.call_count == 2
    assert mocker.call("first_rez") in fake_commit.call_args_list
    assert mocker.call("second_rez") in fake_commit.call_args_list


@pytest.fixture(scope="function", name="event_bus")
def create_event_bus(mocker):
    """Создает шину событий для тестов."""
    return app.EventBus(mocker.MagicMock(), mocker.AsyncMock())


@pytest.mark.asyncio
async def test_handle_one_command(event_bus, mocker):
    """Тест обработки получения Репо и использования его для обработки события."""
    fake_event = mocker.Mock()

    await event_bus._handle_one_command(fake_event)

    repo = event_bus._uow_factory.return_value.__aenter__.return_value
    event_bus._event_handler.handle_event.assert_called_once_with(fake_event, repo)


@pytest.mark.asyncio
async def test_create_tasks(event_bus, mocker):
    """Создания множества заданий по обработке."""
    fake_command = mocker.patch.object(event_bus, "_handle_one_command")

    fut_set = event_bus._create_tasks(list(range(5)))

    assert isinstance(fut_set, set)
    assert len(fut_set) == 5
    assert fake_command.call_count == 5


def test_handle_event(event_bus, mocker):
    """Количество обработок событий соответствует количеству порождаемых дочерних событий."""
    fake_command = mocker.patch.object(
        event_bus,
        "_handle_one_command",
        side_effect=[[1, 2, 3], [1, 2], [], [], [], []],
    )

    event_bus.handle_event("event")

    assert fake_command.call_count == 6
