import asyncio
import zoneinfo
from datetime import date, datetime, timedelta
from enum import StrEnum, auto
from typing import Final, Protocol

from pydantic import Field

from poptimizer.core import actors, consts, domain, message
from poptimizer.data.cpi import cpi
from poptimizer.data.div import div
from poptimizer.data.moex import quotes, securities

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
    portfolio_day: domain.Day = consts.START_DAY
    features_day: domain.Day | None = None


class MemoryChecker(Protocol):
    def check_memory_usage(self, ctx: actors.Ctx) -> None: ...


class MigrationClient(Protocol):
    async def migrate(self, ctx: actors.Ctx, last_version: str) -> bool: ...


class MOEXClient(securities.MOEXClient, quotes.MOEXClient, Protocol): ...


class DataUpdater:
    def __init__(
        self,
        memory_checker: MemoryChecker,
        migration_client: MigrationClient,
        cdr_client: cpi.CBRClient,
        moex_client: MOEXClient,
        evolution_aid: actors.AID,
    ) -> None:
        self._memory_checker = memory_checker
        self._migration_client = migration_client
        self._cbr_client = cdr_client
        self._moex_client = moex_client
        self._evolution_aid = evolution_aid

    async def __call__(self, ctx: actors.Ctx, state: DataState, msg: message.AppStarted | message.Next) -> None:
        match (msg, state.state):
            case (message.AppStarted(version=version), _):
                await self._migrate(ctx, state, version)
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

    async def _migrate(self, ctx: actors.Ctx, state: DataState, version: str) -> None:
        if await self._migration_client.migrate(ctx, state.app_version):
            state.state = _StateName.UPDATING_DATA
            state.features_day = None

        state.app_version = version

    async def _update_data(self, ctx: actors.Ctx, state: DataState) -> None:
        next_check_day = _last_finished_day()

        async with asyncio.TaskGroup() as tg:
            tg.create_task(cpi.update(ctx, self._cbr_client))
            sec_task = tg.create_task(securities.update(ctx, self._moex_client))
            tg.create_task(div.update(ctx, sec_task))
            trading_days_task = tg.create_task(quotes.update(ctx, self._moex_client, next_check_day, sec_task))

        state.state = _StateName.UPDATING_PORTFOLIO
        state.check_day = next_check_day
        state.data_day = (await trading_days_task)[-1]

    async def _update_portfolio(self, ctx: actors.Ctx, state: DataState) -> None:  # noqa: ARG002
        if state.portfolio_day < state.data_day:
            ...

        state.state = _StateName.UPDATING_FEATURES
        state.portfolio_day = state.data_day

    async def _update_features(self, ctx: actors.Ctx, state: DataState) -> None:  # noqa: ARG002
        if state.features_day is None or state.features_day < state.data_day:
            ...

        state.state = _StateName.WAITING_EVOLUTION
        state.features_day = state.data_day

    async def _check_day_changed(self, ctx: actors.Ctx, state: DataState) -> None:
        if _last_finished_day() > state.check_day:
            state.state = _StateName.UPDATING_DATA
            ctx.send(message.Next())
