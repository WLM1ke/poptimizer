from poptimizer.core import consts, domain, fsm
from poptimizer.data import events
from poptimizer.fsm import graph


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


def build_graph() -> graph.Graph:
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
    )
    data_graph.register_event(
        events.VersionNotChanged,
    )

    return data_graph
