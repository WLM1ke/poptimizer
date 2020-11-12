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
        """Запускает обновление необходимых таблиц в конце торгового дня."""
        new_events: List[domain.AbstractEvent] = [
            events.IndexCalculated("MCFTRR", event.date),
            events.IndexCalculated("RVI", event.date),
        ]

        table_groups = [
            base.CPI,
            base.SECURITIES,
            base.SMART_LAB,
        ]

        for group in table_groups:
            table_id = base.create_id(group)
            table = await repo.get(table_id)
            new_events.extend(await table.handle_event(event))

        return new_events

    @handle_event.register
    async def ticker_traded(
        self,
        event: events.TickerTraded,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицы с котировками и дивидендами."""
        new_events = []

        table_groups = [base.QUOTES, base.DIVIDENDS]

        for group in table_groups:
            table_id = base.create_id(group, event.ticker)
            table = await repo.get(table_id)
            new_events.extend(await table.handle_event(event))

        return new_events

    @handle_event.register
    async def index_calculated(
        self,
        event: events.IndexCalculated,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками индексов."""
        table_id = base.create_id(base.INDEX, event.ticker)
        table = await repo.get(table_id)
        return await table.handle_event(event)

    @handle_event.register
    async def div_expected(
        self,
        event: events.DivExpected,
        repo: domain.AbstractRepo[base.AbstractTable[domain.AbstractEvent]],
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками."""
        print(event)
        return []
