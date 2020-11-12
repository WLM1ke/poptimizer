"""Обработчики доменных событий."""
import functools
from typing import List

from poptimizer import config
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base
from poptimizer.data_di.shared import domain


class UnknownEventError(config.POptimizerError):
    """Для события не зарегистрирован обработчик."""


class EventHandlersDispatcher(domain.AbstractHandler[base.AbstractTable[domain.AbstractEvent]]):
    """Обеспечивает запуск обработчика в соответствии с типом события."""

    @functools.singledispatchmethod
    async def handle_event(
        self,
        event: domain.AbstractEvent,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обработчик для отсутствующих событий."""
        raise UnknownEventError(event)

    @handle_event.register
    async def app_started(
        self,
        event: events.AppStarted,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = base.create_id(base.TRADING_DATES)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def trading_day_ended(
        self,
        event: events.TradingDayEnded,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Создает события, связанные с обновлением данных в конце торгового дня."""
        table_id = base.create_id(base.CPI, base.CPI)
        table = await repo.get(table_id)
        new_events = await table.handle_event(event)
        new_events.extend(
            [
                events.TradingDayEndedTQBR(event.date),
                events.IndexCalculated("MCFTRR", event.date),
                events.IndexCalculated("RVI", event.date),
            ]
        )
        return new_events

    @handle_event.register
    async def trading_day_ended_tqbr(
        self,
        event: events.TradingDayEndedTQBR,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с торгуемыми бумагами в режиме TQBR."""
        table_id = base.create_id(base.SECURITIES)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def ticker_traded(
        self,
        event: events.TickerTraded,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками и создает событие по обновлению дивидендов."""
        table_id = base.create_id(base.QUOTES, event.ticker)
        table = await repo.get(table_id)
        new_events = await table.handle_event(event)
        new_events.append(events.DividendsObsoleted(base.DIVIDENDS, event.ticker))
        return new_events

    @handle_event.register
    async def dividends_obsoleted(
        self,
        event: events.DividendsObsoleted,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с дивидендами."""
        table_id = base.create_id(event.group, event.ticker)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def index_calculated(
        self,
        event: events.IndexCalculated,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками."""
        table_id = base.create_id(base.INDEX, event.ticker)
        table = await repo.get(table_id)
        return await table.handle_event(event)
