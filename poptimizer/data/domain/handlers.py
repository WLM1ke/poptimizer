"""Обработчики доменных событий."""
import asyncio
import dataclasses
import functools
import itertools

from poptimizer import config
from poptimizer.data import ports
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import col, domain


class UnknownEventError(config.POptimizerError):
    """Для события не зарегистрирован обработчик."""


AnyTable = base.AbstractTable[domain.AbstractEvent]
AnyTableRepo = domain.AbstractRepo[AnyTable]


async def _load_by_id_and_handle_event(
    repo: AnyTableRepo,
    table_id: domain.ID,
    event: domain.AbstractEvent,
) -> list[domain.AbstractEvent]:
    """Загружает таблицу и обрабатывает событие."""
    table = await repo(table_id)
    return await table.handle_event(event)


class EventHandlersDispatcher(domain.AbstractHandler[AnyTable]):  # noqa: WPS214
    """Обеспечивает запуск обработчика в соответствии с типом события."""

    @functools.singledispatchmethod
    async def handle_event(
        self,
        event: domain.AbstractEvent,
        repo: AnyTableRepo,
    ) -> list[domain.AbstractEvent]:
        """Обработчик для отсутствующих событий."""
        raise UnknownEventError(event)

    @handle_event.register
    async def app_started(
        self,
        event: events.DateCheckRequired,
        repo: AnyTableRepo,
    ) -> list[domain.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = base.create_id(ports.TRADING_DATES)
        return await _load_by_id_and_handle_event(repo, table_id, event)

    @handle_event.register
    async def trading_day_ended(
        self,
        event: events.TradingDayEnded,
        repo: AnyTableRepo,
    ) -> list[domain.AbstractEvent]:
        """Запускает обновление необходимых таблиц в конце торгового дня и создает дочерние события."""
        table_groups = [ ports.RF, ports.DIV_NEW, ports.USD] #ports.CPI,
        table_ids = [base.create_id(group) for group in table_groups]
        aws = [_load_by_id_and_handle_event(repo, id_, event) for id_ in table_ids]
        return [
            events.IndexCalculated("MCFTRR", event.date),
            events.IndexCalculated("MEOGTRR", event.date),
            events.IndexCalculated("IMOEX", event.date),
            events.IndexCalculated("RVI", event.date),
            *itertools.chain.from_iterable(await asyncio.gather(*aws)),
        ]

    @handle_event.register
    async def usd_traded(
        self,
        event: events.USDUpdated,
        repo: AnyTableRepo,
    ) -> list[domain.AbstractEvent]:
        """Запускает обновления перечня торгуемых бумаг."""
        table_id = base.create_id(ports.SECURITIES)
        return await _load_by_id_and_handle_event(repo, table_id, event)

    @handle_event.register
    async def ticker_traded(
        self,
        event: events.TickerTraded,
        repo: AnyTableRepo,
    ) -> list[domain.AbstractEvent]:
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
    ) -> list[domain.AbstractEvent]:
        """Обновляет таблицу с котировками индексов."""
        table_id = base.create_id(ports.INDEX, event.ticker)
        return await _load_by_id_and_handle_event(repo, table_id, event)

    @handle_event.register
    async def update_div(
        self,
        event: events.UpdateDivCommand,
        repo: AnyTableRepo,
    ) -> list[domain.AbstractEvent]:
        """Обновляет таблицы с дивидендами."""
        usd = await repo(base.create_id(ports.USD))
        securities = await repo(base.create_id(ports.SECURITIES))

        enriched_event = dataclasses.replace(
            event,
            type_=securities.df.loc[event.ticker, col.TICKER_TYPE],
            usd=usd.df,
        )

        div_id = base.create_id(ports.DIVIDENDS, event.ticker)
        div_ext_id = base.create_id(ports.DIV_EXT, event.ticker)

        return [
            *await _load_by_id_and_handle_event(repo, div_id, enriched_event),
            *await _load_by_id_and_handle_event(repo, div_ext_id, enriched_event),
        ]
