from poptimizer.data.events import QuotesUpdated
from poptimizer.evolve.events import ModelDeleted
from poptimizer.fsm import graph
from poptimizer.portfolio import actions, events


def build_graph(tinkoff_client: actions.TinkoffClient) -> graph.Graph:
    portfolio_graph = graph.Graph("PortfolioFSM")

    portfolio_graph.add_state(
        events.PortfolioUpdated,
        [
            (QuotesUpdated, actions.RevaluePortfolioAction(), events.PortfolioUpdated),
            (ModelDeleted, actions.CheckPositionsAction(tinkoff_client), events.PortfolioUpdated),
        ],
    )

    return portfolio_graph
