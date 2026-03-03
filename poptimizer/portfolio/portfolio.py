from poptimizer.data.events import DataUpdated
from poptimizer.fsm import graph
from poptimizer.portfolio import actions, events


def build_graph() -> graph.Graph:
    portfolio_graph = graph.Graph("PortfolioFSM", events.PortfolioUpdated)

    portfolio_graph.register_event(
        events.PortfolioUpdated,
        {DataUpdated},
    )
    portfolio_graph.register_event(
        DataUpdated,
        {events.PortfolioUpdated},
        actions.RevaluePortfolioAction(),
    )

    return portfolio_graph
