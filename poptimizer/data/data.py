from poptimizer.core import fsm
from poptimizer.data import actions, events
from poptimizer.evolve.events import ModelRejected
from poptimizer.fsm import graph
from poptimizer.portfolio.events import PortfolioRevalued


def build_graph(
    migration_client: actions.MigrationClient,
    data_client: actions.DataClient,
    memory_checker: actions.MemoryChecker,
) -> graph.Graph:
    data_graph = graph.Graph("DataFSM")

    data_graph.add_state(
        fsm.AppStopped,
        [
            graph.Transition(
                on=fsm.AppStarted,
                action=actions.CheckDataStatusAction(migration_client),
                dst=fsm.AppStarted,
            ),
        ],
    )
    data_graph.add_state(
        fsm.AppStarted,
        [
            graph.Transition(
                on=events.VersionChanged,
                action=actions.MigrateAction(migration_client),
                dst=events.VersionChanged,
            ),
            graph.Transition(
                on=events.QuotesUpdateRequired,
                action=actions.UpdateQuotesAction(data_client),
                dst=events.QuotesUpdateRequired,
            ),
            graph.Transition(
                on=events.DataUpdated,
                action=None,
                dst=events.DataUpdated,
            ),
        ],
    )
    data_graph.add_state(
        events.VersionChanged,
        [
            graph.Transition(
                on=events.QuotesUpdateRequired,
                action=actions.UpdateQuotesAction(data_client),
                dst=events.QuotesUpdateRequired,
            ),
        ],
    )
    data_graph.add_state(
        events.QuotesUpdateRequired,
        [
            graph.Transition(
                on=events.QuotesUpdated,
                action=None,
                dst=events.QuotesUpdated,
            ),
            graph.Transition(
                on=events.DataUpdated,
                action=None,
                dst=events.DataUpdated,
            ),
        ],
    )
    data_graph.add_state(
        events.QuotesUpdated,
        [
            graph.Transition(
                on=PortfolioRevalued,
                action=actions.UpdateFeaturesAction(data_client),
                dst=PortfolioRevalued,
            ),
        ],
    )
    data_graph.add_state(
        PortfolioRevalued,
        [
            graph.Transition(
                on=events.DataUpdated,
                action=None,
                dst=events.DataUpdated,
            ),
        ],
    )
    data_graph.add_state(
        events.DataUpdated,
        [
            graph.Transition(
                on=ModelRejected,
                action=actions.CheckDayAction(memory_checker),
                dst=ModelRejected,
            ),
        ],
    )
    data_graph.add_state(
        ModelRejected,
        [
            graph.Transition(
                on=events.QuotesUpdateRequired,
                action=actions.UpdateQuotesAction(data_client),
                dst=events.QuotesUpdateRequired,
            ),
            graph.Transition(
                on=events.DayNotChanged,
                action=None,
                dst=events.DataUpdated,
            ),
        ],
    )

    return data_graph
