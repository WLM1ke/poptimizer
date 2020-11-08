"""Обработчики доменных событий."""
import functools
from typing import List

from poptimizer import config
from poptimizer.data_di.domain import events, tables
from poptimizer.data_di.shared import domain


class UnknownEventError(config.POptimizerError):
    """Для события не зарегистрирован обработчик."""


class EventHandlersDispatcher(domain.AbstractHandler[tables.AbstractTable[domain.AbstractEvent]]):
    """Обеспечивает запуск обработчика в соответствии с типом события."""

    @functools.singledispatchmethod
    async def handle_event(
        self,
        event: domain.AbstractEvent,
        repo: domain.AbstractRepo[tables.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обработчик для отсутствующих событий."""
        raise UnknownEventError(event)

    @handle_event.register
    async def app_started(
        self,
        event: events.AppStarted,
        repo: domain.AbstractRepo[tables.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = tables.create_id(tables.TRADING_DATES)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def trading_day_ended(
        self,
        event: events.TradingDayEnded,
        _: domain.AbstractRepo[tables.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Создает событие об окончании торгового дня в режиме TQBR."""
        return [events.TradingDayEndedTQBR(event.date)]

    @handle_event.register
    async def trading_day_ended_tqbr(
        self,
        event: events.TradingDayEndedTQBR,
        repo: domain.AbstractRepo[tables.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с торгуемыми бумагами в режиме TQBR."""
        table_id = tables.create_id(tables.SECURITIES)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def ticker_traded(
        self,
        event: events.TickerTraded,
        repo: domain.AbstractRepo[tables.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками."""
        print(event)
        return []
