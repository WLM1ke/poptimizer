import asyncio
import zoneinfo
from datetime import date, datetime, timedelta
from enum import StrEnum, auto
from typing import Final

from poptimizer.actors.data.cpi import cpi
from poptimizer.actors.data.div import div
from poptimizer.actors.data.moex import securities
from poptimizer.core import actors, adapters, consts, domain, message

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 01.00
_END_HOUR: Final = 1
_END_MINUTE: Final = 0


class _StateName(StrEnum):
    DATA_MIGRATED = auto()
    DATA_CHECK_REQUIRED = auto()
    NEW_DATA_AVAILABLE = auto()
    DATA_UPDATED = auto()


class DataState(actors.State[_StateName]):
    state: _StateName = _StateName.NEW_DATA_AVAILABLE
    app_version: str = ""
    last_trading_day: domain.Day = consts.START_DAY
    checked_at: domain.Day = consts.START_DAY


class DataUpdater:
    def __init__(
        self,
        memory_checker: adapters.MemoryChecker,
        migration_client: adapters.MigrationClient,
        cdr_client: adapters.CBRClient,
        moex_client: adapters.MOEXClient,
        evolution_aid: actors.AID,
    ) -> None:
        self._memory_checker = memory_checker
        self._migration_client = migration_client
        self._cbr_client = cdr_client
        self._moex_client = moex_client
        self._evolution_aid = evolution_aid

    async def __call__(self, ctx: actors.Ctx, state: DataState, msg: message.AppStarted | message.Next) -> None:
        aid: actors.AID | None = None

        match (msg, state.state):
            case (message.AppStarted(), _):
                if await self._migration_client.migrate(ctx, state.app_version):
                    state.state = _StateName.DATA_MIGRATED

                state.app_version = msg.version

                if await self._is_new_data_available(state):
                    state.state = _StateName.NEW_DATA_AVAILABLE
            case (message.Next(), _StateName.DATA_MIGRATED):
                await self._update_data_and_features(ctx, state)
            case (message.Next(), _StateName.DATA_CHECK_REQUIRED):
                self._memory_checker.check_memory_usage(ctx)

                state.state = _StateName.DATA_UPDATED
                if await self._is_new_data_available(state):
                    state.state = _StateName.NEW_DATA_AVAILABLE
            case (message.Next(), _StateName.NEW_DATA_AVAILABLE):
                await self._update_all(ctx, state)
                state.state = _StateName.DATA_UPDATED
            case (message.Next(), _StateName.DATA_UPDATED):
                await asyncio.sleep(60 * 60)
                state.state = _StateName.DATA_CHECK_REQUIRED
                aid = self._evolution_aid

        ctx.send(message.Next(), aid=aid)

    async def _is_new_data_available(self, state: DataState) -> bool:
        last_finished_day = _last_finished_day()

        if state.checked_at >= last_finished_day:
            return False

        new_last_trading_day = min(last_finished_day, await self._moex_client.last_trading_day())

        if state.last_trading_day >= new_last_trading_day:
            state.checked_at = last_finished_day

            return False

        return True

    async def _update_all(self, ctx: actors.Ctx, state: DataState) -> None:
        await self._update_data(ctx, state)

    async def _update_data_and_features(self, ctx: actors.Ctx, state: DataState) -> None:
        await self._update_data(ctx, state)

    async def _update_data(self, ctx: actors.Ctx, state: DataState) -> None:  # noqa: ARG002
        async with asyncio.TaskGroup() as tg:
            tg.create_task(ctx.run_safe(cpi.update, self._cbr_client))
            sec_task = tg.create_task(ctx.run_with_retry(securities.update, self._moex_client))
            tg.create_task(ctx.run_with_retry(div.update, sec_task))


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
