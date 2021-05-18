"""Тестирование запуска приложения."""
from poptimizer.data.app import bootstrap, viewers
from poptimizer.data.domain import events


def test_start_app(mocker):
    """Должна запускаться шина с обработкой события начала работы и  viewer."""
    fake_bus = mocker.patch.object(bootstrap.app, "EventBus")

    bus, viewer = bootstrap.start_app()

    assert bus is fake_bus.return_value
    assert isinstance(viewer, viewers.Viewer)
    bus.handle_event.assert_called_once()

    args, kwargs = bus.handle_event.call_args
    assert len(args) == 1
    assert isinstance(args[0], events.DateCheckRequired)
    assert not kwargs
