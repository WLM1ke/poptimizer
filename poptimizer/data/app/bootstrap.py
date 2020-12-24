"""Запуск приложения - инициализация event bus и viewer."""
import datetime
from typing import Final, Tuple

from poptimizer.data.adapters import odm
from poptimizer.data.app import viewers
from poptimizer.data.domain import events
from poptimizer.data.domain import factory, handlers
from poptimizer.data.domain.tables import base
from poptimizer.shared import adapters, app, domain

# Параметры представления конечных данных
# До 2015 года не у всех бумаг был режим T+2
# У некоторых бумаг происходило слияние без изменения тикера (IRAO)
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)

# Параметры налогов
TAX: Final = 0.13
AFTER_TAX: Final = 1 - TAX


TableBus = app.EventBus[base.AbstractTable[domain.AbstractEvent]]


def start_app() -> Tuple[TableBus, viewers.Viewer]:
    """Запуск приложения.

    Создаются:

    - Шина сообщений
    - Viewer DataFrame таблиц

    Инициируется обработка сообщения начала работы приложения.
    """
    mapper = adapters.Mapper(odm.DATA_DESCRIPTION, factory.TablesFactory())

    bus = app.EventBus(
        lambda: app.UoW(mapper),
        handlers.EventHandlersDispatcher(),
    )
    event = events.AppStarted()
    bus.handle_event(event)

    return bus, viewers.Viewer(mapper)


BUS, VIEWER = start_app()
