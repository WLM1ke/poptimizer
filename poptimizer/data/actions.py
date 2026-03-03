import asyncio
import zoneinfo
from datetime import date, datetime, timedelta
from typing import Final, Protocol

from poptimizer.core import consts, domain, fsm
from poptimizer.data import events
from poptimizer.data.cpi import cpi
from poptimizer.data.div import processed, raw, status
from poptimizer.data.moex import index, quotes, securities

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 01.00
_END_HOUR: Final = 1
_END_MINUTE: Final = 0


def _last_finished_day() -> domain.Day:
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


class DataState(domain.Entity):
    app_version: str = consts.__version__
    check_day: domain.Day = consts.START_DAY
    data_day: domain.Day = consts.START_DAY
    update_required: bool = True


class CheckVersionAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        state = await ctx.get(DataState)

        match state.app_version == consts.__version__:
            case True:
                ctx.send(events.VersionNotChanged())
            case False:
                ctx.send(events.VersionChanged())


class MigrationClient(Protocol):
    async def migrate(self, ctx: fsm.Ctx, last_version: str) -> None: ...


class MigrateAction:
    def __init__(self, migration_client: MigrationClient) -> None:
        self._migration_client = migration_client

    async def __call__(self, ctx: fsm.Ctx) -> None:
        state = await ctx.get_for_update(DataState)
        await self._migration_client.migrate(ctx, state.app_version)
        state.app_version = consts.__version__
        state.update_required = True
        ctx.send(events.UpdateRequired())


class CheckDayAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        last_finished_day = _last_finished_day()
        state = await ctx.get(DataState)

        state.update_required |= state.check_day != last_finished_day

        match state.update_required:
            case True:
                ctx.send(events.UpdateRequired())
            case False:
                ctx.send(events.FeaturesUpdated())


class DataClient(
    index.Client,
    securities.Client,
    quotes.Client,
    status.Client,
    cpi.Client,
    raw.Client,
    Protocol,
): ...


class UpdateDataAction:
    def __init__(self, data_client: DataClient) -> None:
        self._data_client = data_client

    async def __call__(self, ctx: fsm.Ctx) -> None:
        last_finished_day = _last_finished_day()

        async with asyncio.TaskGroup() as tg:
            state_task = tg.create_task(ctx.get_for_update(DataState))
            tg.create_task(index.update(ctx, self._data_client, last_finished_day))
            tg.create_task(cpi.update(ctx, self._data_client))
            sec_task = tg.create_task(securities.update(ctx, self._data_client))
            tg.create_task(processed.update(ctx, sec_task))
            trading_days = await quotes.update(ctx, self._data_client, last_finished_day, sec_task)

        state = await state_task
        state.check_day = last_finished_day

        data_day = trading_days[-1]
        if data_day > state.data_day:
            state.data_day = data_day
            state.update_required = True

        ctx.send(events.DataUpdated(trading_days=trading_days))
