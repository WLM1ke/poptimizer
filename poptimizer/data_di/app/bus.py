"""Шина событий."""
from typing import Final

from poptimizer.data_di.adapters import odm
from poptimizer.data_di.domain import handlers, tables
from poptimizer.data_di.shared import app, domain

AnyTable = tables.AbstractTable[domain.AbstractEvent]


def uow_factory() -> app.UoW[AnyTable]:
    """Фабрика по производству контекстов транзакции."""
    return app.UoW(odm.MAPPER)


EVENT_BUS: Final = app.EventBus(
    uow_factory,
    handlers.EventHandlersDispatcher(),
)
