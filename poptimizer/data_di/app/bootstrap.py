"""Шина событий."""
import datetime
from typing import Final

from poptimizer.data_di.adapters import odm
from poptimizer.data_di.app import viewers
from poptimizer.data_di.domain import events, handlers
from poptimizer.data_di.domain.tables import base
from poptimizer.data_di.shared import adapters, app

# База данных с таблицами
_DB = adapters.MONGO_CLIENT[base.PACKAGE]

# Параметры представления конечных данных
# До 2015 года не у всех бумаг был режим T+2
# У некоторых бумаг происходило слияние без изменения тикера (IRAO)
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)

# Параметры налогов
TAX: Final = 0.13
AFTER_TAX: Final = 1 - TAX


def start_app() -> viewers.Viewer:
    """Создает шину сообщений и инициирует обработку сообщения начала работы приложения."""
    bus = app.EventBus(
        lambda: app.UoW(odm.MAPPER),
        handlers.EventHandlersDispatcher(),
    )
    event = events.AppStarted()
    bus.handle_event(event)
    return viewers.Viewer(_DB)


VIEWER: Final = start_app()
