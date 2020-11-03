"""Шина событий."""
from typing import Final

from poptimizer.data_di.adapters import odm
from poptimizer.data_di.domain import events, handlers, tables
from poptimizer.data_di.shared import app, domain


def start_app() -> app.EventBus[tables.AbstractTable[domain.AbstractEvent]]:
    """Создает шину сообщений и инициирует обработку сообщения начала работы приложения."""
    bus = app.EventBus(
        lambda: app.UoW(odm.MAPPER),
        handlers.EventHandlersDispatcher(),
    )
    event = events.AppStarted()
    bus.handle_event(event)
    return bus


EVENT_BUS: Final = start_app()
