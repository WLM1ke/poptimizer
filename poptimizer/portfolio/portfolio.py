from poptimizer.data.events import QuotesUpdated
from poptimizer.fsm import graph
from poptimizer.portfolio import actions, events


def build_graph() -> graph.Graph:
    portfolio_graph = graph.Graph("PortfolioFSM")

    portfolio_graph.add_state(
        events.PortfolioUpdated,
        [(QuotesUpdated, actions.RevaluePortfolioAction(), events.PortfolioUpdated)],
    )

    return portfolio_graph
