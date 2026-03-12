from poptimizer.core import fsm
from poptimizer.data import actions, events
from poptimizer.evolve.events import ModelDeleted
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
        [(fsm.AppStarted, actions.CheckDataStatusAction())],
    )
    data_graph.add_state(
        fsm.AppStarted,
        [
            (events.VersionChanged, actions.MigrateAction(migration_client)),
            (events.QuotesUpdateRequired, actions.UpdateQuotesAction(data_client)),
            events.DataUpdated,
        ],
    )
    data_graph.add_state(
        events.VersionChanged,
        [(events.QuotesUpdateRequired, actions.UpdateQuotesAction(data_client))],
    )
    data_graph.add_state(
        events.QuotesUpdateRequired,
        [
            events.QuotesUpdated,
            events.DataUpdated,
        ],
    )
    data_graph.add_state(
        events.QuotesUpdated,
        [(PortfolioRevalued, actions.UpdateFeaturesAction(data_client))],
    )
    data_graph.add_state(
        PortfolioRevalued,
        [events.DataUpdated],
    )
    data_graph.add_state(
        events.DataUpdated,
        [(ModelDeleted, actions.CheckDayAction(memory_checker))],
    )
    data_graph.add_state(
        ModelDeleted,
        [
            (events.QuotesUpdateRequired, actions.UpdateQuotesAction(data_client)),
            (events.DayNotChanged, None, events.DataUpdated),
        ],
    )

    return data_graph
