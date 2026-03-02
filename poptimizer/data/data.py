import zoneinfo
from datetime import date, datetime, timedelta
from typing import Final, Protocol

from poptimizer.core import consts, domain, fsm
from poptimizer.data import events
from poptimizer.data.features import features
from poptimizer.fsm import graph

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 01.00
_END_HOUR: Final = 1
_END_MINUTE: Final = 0


def _last_finished_day() -> domain.Day:  # type: ignore  # noqa: PGH003
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
        await ctx.drop(features.Features)
        state = await ctx.get_for_update(DataState)
        await self._migration_client.migrate(ctx, state.app_version)
        state.app_version = consts.__version__
        ctx.send(events.UpdateRequired())


def build_graph(
    migration_client: MigrationClient,
) -> graph.Graph:
    data_graph = graph.Graph("DataFSM", events.AppStopped)

    data_graph.register_event(
        events.AppStopped,
        {events.AppStarted},
    )
    data_graph.register_event(
        events.AppStarted,
        {events.VersionChanged, events.VersionNotChanged},
        CheckVersionAction(),
    )
    data_graph.register_event(
        events.VersionChanged,
        {events.UpdateRequired},
        MigrateAction(migration_client),
    )
    data_graph.register_event(
        events.VersionNotChanged,
    )
    data_graph.register_event(
        events.UpdateRequired,
    )

    return data_graph
