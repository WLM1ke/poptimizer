"""Шина событий."""
from typing import Final

from poptimizer.data_di.adapters import odm
from poptimizer.data_di.app import viewer
from poptimizer.data_di.domain import events, handlers
from poptimizer.data_di.domain.tables import base
from poptimizer.data_di.shared import adapters, app

# База данных с таблицами
_DB = adapters.MONGO_CLIENT[base.PACKAGE]


def start_app() -> viewer.Viewer:
    """Создает шину сообщений и инициирует обработку сообщения начала работы приложения."""
    bus = app.EventBus(
        lambda: app.UoW(odm.MAPPER),
        handlers.EventHandlersDispatcher(),
    )
    event = events.AppStarted()
    bus.handle_event(event)
    return viewer.Viewer(_DB)


VIEWER: Final = start_app()
