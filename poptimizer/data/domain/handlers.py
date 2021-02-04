"""Обработчики доменных событий."""
import asyncio
import functools
import itertools
from typing import List

import pandas as pd

from poptimizer import config
from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import domain


class UnknownEventError(config.POptimizerError):
    """Для события не зарегистрирован обработчик."""


AnyTable = base.AbstractTable[domain.AbstractEvent]
AnyTableRepo = domain.AbstractRepo[AnyTable]


async def _load_by_id_and_handle_event(
    repo: AnyTableRepo,
    table_id: domain.ID,
    event: domain.AbstractEvent,
) -> List[domain.AbstractEvent]:
    """Загружает таблицу и обрабатывает событие."""
    table = await repo.get(table_id)
    return await table.handle_event(event)


class EventHandlersDispatcher(domain.AbstractHandler[AnyTable]):
    """Обеспечивает запуск обработчика в соответствии с типом события."""

    @functools.singledispatchmethod
    async def handle_event(
        self,
        event: domain.AbstractEvent,
        repo: AnyTableRepo,
    ) -> List[domain.AbstractEvent]:
        """Обработчик для отсутствующих событий."""
        raise UnknownEventError(event)

    @handle_event.register
    async def app_started(
        self,
        event: events.AppStarted,
        repo: AnyTableRepo,
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = base.create_id(ports.TRADING_DATES)
        return await _load_by_id_and_handle_event(repo, table_id, event)

    @handle_event.register
    async def trading_day_ended(
        self,
        event: events.TradingDayEnded,
        repo: AnyTableRepo,
    ) -> List[domain.AbstractEvent]:
        """Запускает обновление необходимых таблиц в конце торгового дня и создает дочерние события."""
        table_groups = [ports.CPI, ports.SECURITIES, ports.SMART_LAB, ports.USD]
        table_ids = [base.create_id(group) for group in table_groups]
        aws = [_load_by_id_and_handle_event(repo, id_, event) for id_ in table_ids]
        return [
            events.IndexCalculated("MCFTRR", event.date),
            events.IndexCalculated("IMOEX", event.date),
            events.IndexCalculated("RVI", event.date),
            *itertools.chain.from_iterable(await asyncio.gather(*aws)),
        ]

    @handle_event.register
    async def ticker_traded(
        self,
        event: events.TickerTraded,
        repo: AnyTableRepo,
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицы с котировками и дивидендами."""
        table_groups = [ports.QUOTES, ports.DIVIDENDS]
        table_ids = [base.create_id(group, event.ticker) for group in table_groups]
        aws = [_load_by_id_and_handle_event(repo, id_, event) for id_ in table_ids]
        return list(itertools.chain.from_iterable(await asyncio.gather(*aws)))

    @handle_event.register
    async def index_calculated(
        self,
        event: events.IndexCalculated,
        repo: AnyTableRepo,
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с котировками индексов."""
        table_id = base.create_id(ports.INDEX, event.ticker)
        return await _load_by_id_and_handle_event(repo, table_id, event)

    @handle_event.register
    async def div_expected(
        self,
        event: events.DivExpected,
        repo: AnyTableRepo,
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицу с внешними дивидендами."""
        table_id = base.create_id(ports.DIV_EXT, event.ticker)
        return await _load_by_id_and_handle_event(repo, table_id, event)

    @handle_event.register
    async def update_div(
        self,
        event: events.UpdateDivCommand,
        repo: AnyTableRepo,
    ) -> List[domain.AbstractEvent]:
        """Обновляет таблицы с котировками и дивидендами."""
        table_id = base.create_id(ports.DIVIDENDS, event.ticker)
        return [
            events.DivExpected(event.ticker, pd.DataFrame(columns=["SmartLab"])),
            *await _load_by_id_and_handle_event(repo, table_id, event),
        ]
