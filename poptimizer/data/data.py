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
        [(events.AppStarted, actions.CheckDataStatusAction())],
    )
    data_graph.add_state(
        events.AppStarted,
        [
            (events.VersionChanged, actions.MigrateAction(migration_client)),
            (events.QuotesUpdateRequired, actions.UpdateQuotesAction(data_client)),
            (events.DataUpdated, actions.WaitNewDayAction()),
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
            (events.DataUpdated, actions.WaitNewDayAction()),
        ],
    )
    data_graph.add_state(
        events.QuotesUpdated,
        [(PortfolioRevalued, actions.UpdateFeaturesAction(data_client))],
    )
    data_graph.add_state(
        PortfolioRevalued,
        [(events.DataUpdated, actions.WaitNewDayAction())],
    )
    data_graph.add_state(
        events.DataUpdated,
        [(events.QuotesUpdateRequired, actions.UpdateQuotesAction(data_client))],
    )

    return data_graph
