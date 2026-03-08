import asyncio
import zoneinfo
from datetime import date, datetime, timedelta
from typing import Final, Protocol

from poptimizer.core import consts, domain, fsm
from poptimizer.data import events
from poptimizer.data.cpi import cpi
from poptimizer.data.div import processed, raw, status
from poptimizer.data.features import day as day_features
from poptimizer.data.features import indexes as indexes_features
from poptimizer.data.features import quotes as quotes_features
from poptimizer.data.features import securities as securities_features
from poptimizer.data.moex import index, quotes, securities
from poptimizer.portfolio.events import PortfolioRevalued

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


def _next_check_delay(last_check_day: domain.Day) -> timedelta:
    return (
        datetime(
            year=last_check_day.year,
            month=last_check_day.month,
            day=last_check_day.day,
            hour=_END_HOUR,
            minute=_END_MINUTE,
            tzinfo=_MOEX_TZ,
        )
        + timedelta(days=2)
        - datetime.now(_MOEX_TZ)
    )


class DataState(domain.Entity):
    app_version: str = consts.__version__
    check_day: domain.Day = consts.START_DAY
    data_day: domain.Day = consts.START_DAY
    outdated: bool = True


class CheckDataStatusAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        state = await ctx.get(DataState)

        event = events.DataUpdated()

        if state.outdated or state.check_day != _last_finished_day():
            event = events.QuotesUpdateRequired()

        if state.app_version != consts.__version__:
            event = events.VersionChanged()

        ctx.send(event)


class MigrationClient(Protocol):
    async def migrate(self, ctx: fsm.Ctx, last_version: str) -> None: ...


class MigrateAction:
    def __init__(self, migration_client: MigrationClient) -> None:
        self._migration_client = migration_client

    async def __call__(self, ctx: fsm.Ctx) -> None:
        state = await ctx.get_for_update(DataState)
        await self._migration_client.migrate(ctx, state.app_version)
        state.app_version = consts.__version__
        state.outdated = True
        ctx.send(events.QuotesUpdateRequired())


class DataClient(
    index.Client,
    securities.Client,
    quotes.Client,
    status.Client,
    cpi.Client,
    raw.Client,
    Protocol,
): ...


class UpdateQuotesAction:
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
            state.outdated = True

        event = events.DataUpdated()
        if state.outdated:
            event = events.QuotesUpdated(trading_days=trading_days)

        ctx.send(event)


class UpdateFeaturesAction:
    def __init__(self, data_client: DataClient) -> None:
        self._data_client = data_client

    async def __call__(self, ctx: fsm.Ctx, event: PortfolioRevalued) -> None:
        async with asyncio.TaskGroup() as tg:
            state_task = tg.create_task(ctx.get_for_update(DataState))
            status_task = tg.create_task(status.update(ctx, self._data_client))
            tg.create_task(raw.update(ctx, self._data_client, status_task))
            await quotes_features.update(ctx, event.trading_days)
            tg.create_task(indexes_features.update(ctx, event.trading_days))
            tg.create_task(securities_features.update(ctx))
            tg.create_task(day_features.update(ctx, event.trading_days))

        state = await state_task
        state.outdated = False
        ctx.send(events.DataUpdated())


class WaitNewDayAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        state = await ctx.get(DataState)

        delay = _next_check_delay(state.check_day)
        ctx.info(f"Waiting for new day {delay}")

        await asyncio.sleep(delay.total_seconds())

        ctx.send(events.QuotesUpdateRequired())
