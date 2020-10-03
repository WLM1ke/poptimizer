"""Тесты обработчиков на получение данных из таблиц."""
from poptimizer.data.app import handlers
from poptimizer.data.domain import events
from poptimizer.data.ports import outer


def test_run_command(mocker):
    """Получение результата из асинхронного обработчика."""
    fake_loop = mocker.Mock()
    fake_event_bus = mocker.patch.object(handlers.event_bus, "EventBus").return_value
    fake_command = mocker.sentinel

    command_rez = handlers.Handler(fake_loop, mocker.sentinel)._run_commands(fake_command)

    fake_event_bus.handle_events.assert_called_once_with(fake_command)
    fake_loop.run_until_complete.assert_called_once_with(fake_event_bus.handle_events.return_value)
    assert command_rez is fake_loop.run_until_complete.return_value


def test_get_df(mocker):
    """Передача команды на получение данных из одной таблицы."""
    df_getter = handlers.Handler(mocker.sentinel, mocker.sentinel)
    table_name = outer.TableName(outer.QUOTES, "AKRN")
    fake_run_commands = mocker.patch.object(
        df_getter,
        "_run_commands",
        return_value={table_name: "test"},
    )

    assert df_getter.get_df(table_name) == "test"

    fake_run_commands.assert_called_once()
    call_args = fake_run_commands.call_args.args
    assert len(call_args) == 1
    assert len(call_args[0]) == 1
    command = call_args[0][0]
    assert isinstance(command, events.GetDataFrame)
    assert all([command._table_name == table_name, command._force is False])


def test_get_dfs(mocker):
    """Передача команды на получение данных из нескольких таблиц."""
    df_getter = handlers.Handler(mocker.sentinel, mocker.sentinel)
    rez_dict = {
        outer.TableName(outer.QUOTES, "GAZP"): "abc",
        outer.TableName(outer.QUOTES, "NLMK"): "fh",
    }
    fake_run_commands = mocker.patch.object(df_getter, "_run_commands", return_value=rez_dict)

    assert df_getter.get_dfs(outer.QUOTES, ("NLMK", "GAZP")) == ("fh", "abc")

    fake_run_commands.assert_called_once()
    call_args = fake_run_commands.call_args.args
    assert len(call_args) == 1
    assert len(call_args[0]) == 2
