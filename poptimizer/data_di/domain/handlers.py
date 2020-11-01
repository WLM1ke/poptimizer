"""Обработчики доменных событий."""
import functools
from typing import List

from poptimizer import config
from poptimizer.data_di.domain import events, tables
from poptimizer.data_di.shared import domain


class UnknownEventError(config.POptimizerError):
    """Для события не зарегистрирован обработчик."""


class EventHandlersDispatcher(domain.AbstractHandler[domain.AbstractEvent]):
    """Обеспечивает запуск обработчика в соответствии с типом события."""

    def __init__(self, repo: domain.AbstractRepo[tables.AbstractTable[domain.AbstractEvent]]) -> None:
        """Сохраняет репо."""
        self._repo = repo

    @functools.singledispatchmethod
    async def handle_event(self, event: domain.AbstractEvent) -> List[domain.AbstractEvent]:
        """Обработчик для отсутствующих событий."""
        raise UnknownEventError(event)

    @handle_event.register
    async def _(self, event: events.AppStarted) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = tables.create_id("trading_date")
        table = await self._repo.get(table_id)
        return await table.handle_event(event)
