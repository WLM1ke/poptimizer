import asyncio
import zoneinfo
from datetime import date, datetime, timedelta
from enum import StrEnum, auto
from typing import Final, Protocol

from pydantic import Field, PositiveInt

from poptimizer.core import actors, consts, domain, message
from poptimizer.data.cpi import cpi
from poptimizer.data.div import processed, raw, status
from poptimizer.data.features import indexes as indexes_features
from poptimizer.data.features import quotes as quotes_features
from poptimizer.data.moex import index, quotes, securities
from poptimizer.data.portfolio import portfolio

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 01.00
_END_HOUR: Final = 1
_END_MINUTE: Final = 0


def _last_finished_day() -> date:
    now = datetime.now(_MOEX_TZ)
    end_of_trading = now.replace(
        hour=_END_HOUR,
        minute=_END_MINUTE,
        second=0,
        microsecond=0,
        tzinfo=_MOEX_TZ,
    )

    delta = 2
    if end_of_trading < now:
        delta = 1

    return date(
        year=now.year,
        month=now.month,
        day=now.day,
    ) - timedelta(days=delta)


class _StateName(StrEnum):
    UPDATING_DATA = auto()
    UPDATING_PORTFOLIO = auto()
    UPDATING_FEATURES = auto()
    WAITING_EVOLUTION = auto()


class DataState(actors.State[_StateName]):
    state: _StateName = _StateName.UPDATING_DATA
    app_version: str = consts.__version__
    check_day: domain.Day = Field(default_factory=_last_finished_day)
    data_day: domain.Day = consts.START_DAY
    features_day: domain.Day | None = None
    minimal_candles: PositiveInt = consts.INITIAL_MINIMAL_CANDLES


class MemoryChecker(Protocol):
    def check_memory_usage(self, ctx: actors.Ctx) -> None: ...


class MigrationClient(Protocol):
    async def migrate(self, ctx: actors.Ctx, last_version: str) -> bool: ...


class Client(
    index.Client,
    securities.Client,
    quotes.Client,
    status.Client,
    cpi.Client,
    raw.Client,
    Protocol,
): ...


class DataActor:
    def __init__(
        self,
        memory_checker: MemoryChecker,
        migration_client: MigrationClient,
        data_client: Client,
        evolution_aid: actors.AID,
    ) -> None:
        self._memory_checker = memory_checker
        self._migration_client = migration_client
        self._data_client = data_client
        self._evolution_aid = evolution_aid

    async def __call__(self, ctx: actors.Ctx, state: DataState, msg: message.AppStarted | message.Next) -> None:
        match (msg, state.state):
            case (message.AppStarted(), _):
                await self._migrate(ctx, state)
            case (message.Next(), _StateName.UPDATING_DATA):
                await self._update_data(ctx, state)
            case (message.Next(), _StateName.UPDATING_PORTFOLIO):
                await self._update_portfolio(ctx, state)
            case (message.Next(), _StateName.UPDATING_FEATURES):
                await self._update_features(ctx, state)
            case (message.Next(), _StateName.WAITING_EVOLUTION):
                await self._check_day_changed(ctx, state)

                return

        ctx.send(message.Next())

    async def _migrate(self, ctx: actors.Ctx, state: DataState) -> None:
        if await self._migration_client.migrate(ctx, state.app_version):
            state.state = _StateName.UPDATING_DATA
            state.features_day = None

        state.app_version = consts.__version__

    async def _update_data(self, ctx: actors.Ctx, state: DataState) -> None:
        last_finished_day = _last_finished_day()

        async with asyncio.TaskGroup() as tg:
            tg.create_task(index.update(ctx, self._data_client, last_finished_day))
            tg.create_task(cpi.update(ctx, self._data_client))
            sec_task = tg.create_task(securities.update(ctx, self._data_client))
            tg.create_task(processed.update(ctx, sec_task))
            tg.create_task(quotes.update(ctx, self._data_client, last_finished_day, sec_task))

        state.state = _StateName.UPDATING_PORTFOLIO
        state.check_day = last_finished_day

        sec_table = await sec_task
        state.data_day = sec_table.trading_days[-1]

    async def _update_portfolio(self, ctx: actors.Ctx, state: DataState) -> None:
        await portfolio.update(ctx, state.minimal_candles)
        await status.update(ctx, self._data_client)
        await raw.update(ctx, self._data_client)

        state.state = _StateName.UPDATING_FEATURES

    async def _update_features(self, ctx: actors.Ctx, state: DataState) -> None:
        if state.features_day is None or state.features_day < state.data_day:
            await quotes_features.update(ctx)

            async with asyncio.TaskGroup() as tg:
                tg.create_task(indexes_features.update(ctx))

        state.state = _StateName.WAITING_EVOLUTION
        state.features_day = state.data_day

    async def _check_day_changed(self, ctx: actors.Ctx, state: DataState) -> None:
        if _last_finished_day() > state.check_day:
            state.state = _StateName.UPDATING_DATA
            ctx.send(message.Next())
