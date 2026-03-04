from poptimizer.data.events import QuotesUpdated
from poptimizer.fsm import graph
from poptimizer.portfolio import actions, events


def build_graph() -> graph.Graph:
    portfolio_graph = graph.Graph("PortfolioFSM", events.PortfolioUpdated)

    portfolio_graph.register_event(
        events.PortfolioUpdated,
        {QuotesUpdated},
    )
    portfolio_graph.register_event(
        QuotesUpdated,
        {(events.PortfolioRevalued, events.PortfolioUpdated)},
        actions.RevaluePortfolioAction(),
    )

    return portfolio_graph
