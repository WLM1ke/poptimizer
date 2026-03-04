from poptimizer.data import actions, events
from poptimizer.fsm import graph
from poptimizer.portfolio.events import PortfolioRevalued


def build_graph(
    migration_client: actions.MigrationClient,
    data_client: actions.DataClient,
) -> graph.Graph:
    data_graph = graph.Graph("DataFSM", events.AppStopped)

    data_graph.register_event(
        events.AppStopped,
        {events.AppStarted},
    )
    data_graph.register_event(
        events.AppStarted,
        {events.VersionChanged, events.VersionNotChanged},
        actions.CheckVersionAction(),
    )
    data_graph.register_event(
        events.VersionChanged,
        {events.UpdateRequired},
        actions.MigrateAction(migration_client),
    )
    data_graph.register_event(
        events.VersionNotChanged,
        {events.UpdateRequired, events.FeaturesUpdated},
        actions.CheckDayAction(),
    )
    data_graph.register_event(
        events.UpdateRequired,
        {events.QuotesUpdated},
        actions.UpdateQuotesAction(data_client),
    )
    data_graph.register_event(
        events.QuotesUpdated,
        {PortfolioRevalued},
    )
    data_graph.register_event(
        PortfolioRevalued,
    )
    data_graph.register_event(
        events.FeaturesUpdated,
    )
    return data_graph
