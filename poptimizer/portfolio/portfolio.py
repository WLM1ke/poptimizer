from poptimizer.data.events import QuotesUpdated
from poptimizer.evolve.events import ModelRejected
from poptimizer.fsm import graph
from poptimizer.portfolio import actions, events


def build_graph(tinkoff_client: actions.TinkoffClient) -> graph.Graph:
    portfolio_graph = graph.Graph("PortfolioFSM")

    portfolio_graph.add_state(
        events.PortfolioUpdated,
        [
            graph.Transition(
                on=QuotesUpdated,
                action=actions.RevaluePortfolioAction(),
                dst=events.PortfolioUpdated,
            ),
            graph.Transition(
                on=ModelRejected,
                action=actions.CheckPositionsAction(tinkoff_client),
                dst=events.PortfolioUpdated,
            ),
        ],
    )

    return portfolio_graph
