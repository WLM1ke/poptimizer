from poptimizer.data import actions, events
from poptimizer.fsm import graph
from poptimizer.portfolio.events import PortfolioRevalued


def build_graph(
    migration_client: actions.MigrationClient,
    data_client: actions.DataClient,
) -> graph.Graph:
    data_graph = graph.Graph("DataFSM")

    data_graph.add_state(
        events.AppStopped,
        [(events.AppStarted, actions.CheckVersionAction())],
    )
    data_graph.add_state(
        events.AppStarted,
        [
            (events.VersionChanged, actions.MigrateAction(migration_client)),
            (events.VersionNotChanged, actions.CheckDayAction()),
        ],
    )
    data_graph.add_state(
        events.VersionChanged,
        [(events.UpdateRequired, actions.UpdateQuotesAction(data_client))],
    )
    data_graph.add_state(
        events.VersionNotChanged,
        [
            (events.UpdateRequired, actions.UpdateQuotesAction(data_client)),
            events.DataUpdated,
        ],
    )
    data_graph.add_state(
        events.UpdateRequired,
        [events.QuotesUpdated],
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
    )

    return data_graph
