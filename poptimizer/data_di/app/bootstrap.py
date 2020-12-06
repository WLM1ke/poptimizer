"""Шина событий."""
import datetime
from typing import Final

from poptimizer.data_di.adapters import odm
from poptimizer.data_di.app import viewers
from poptimizer.data_di.domain import events, factory, handlers
from poptimizer.data_di.domain.tables import base
from poptimizer.shared import adapters, app, connections, domain

# База данных с таблицами
_DB: Final = connections.MONGO_CLIENT[base.PACKAGE]

# Параметры представления конечных данных
# До 2015 года не у всех бумаг был режим T+2
# У некоторых бумаг происходило слияние без изменения тикера (IRAO)
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)

# Параметры налогов
TAX: Final = 0.13
AFTER_TAX: Final = 1 - TAX


def start_app() -> app.EventBus[base.AbstractTable[domain.AbstractEvent]]:
    """Создает шину сообщений и инициирует обработку сообщения начала работы приложения."""
    mapper = adapters.Mapper(odm.DATA_DESCRIPTION, factory.TablesFactory())
    bus = app.EventBus(
        lambda: app.UoW(mapper),
        handlers.EventHandlersDispatcher(),
    )
    event = events.AppStarted()
    bus.handle_event(event)
    return bus


BUS: Final = start_app()
VIEWER: Final = viewers.Viewer(_DB)
