from poptimizer.core import consts, domain, fsm
from poptimizer.data import events
from poptimizer.fsm import graph


class DataState(domain.Entity):
    app_version: str = consts.__version__


class CheckVersionAction:
    async def __call__(self, ctx: fsm.Ctx, event: events.AppStarted) -> None:  # noqa: ARG002
        state = await ctx.get(DataState)

        match state.app_version == consts.__version__:
            case True:
                ctx.send(events.AppVersionNotChanged())
            case False:
                ctx.send(events.AppVersionChanged())


def build_graph() -> graph.Graph:
    data_graph = graph.Graph("DataFSM", events.AppStarted)

    data_graph.register_event(
        events.AppStarted,
        {events.AppStarted, events.AppVersionChanged, events.AppVersionNotChanged},
        CheckVersionAction(),
    )
    data_graph.register_event(
        events.AppVersionChanged,
    )
    data_graph.register_event(
        events.AppVersionNotChanged,
    )

    return data_graph
