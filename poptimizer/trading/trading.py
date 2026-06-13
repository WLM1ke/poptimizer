from poptimizer.fsm import graph
from poptimizer.portfolio.events import PortfolioRevalued
from poptimizer.trading import actions, events


def build_graph() -> graph.Graph:
    trading_graph = graph.Graph("TradingFSM")

    trading_graph.add_state(
        events.TradingNotRequired,
        [
            graph.Transition(
                on=events.TradingNotRequired,
                dst=events.TradingNotRequired,
            ),
            graph.Transition(
                on=PortfolioRevalued,
                action=actions.InitTradingStateAction(),
                dst=events.TradingNotRequired,
            ),
        ],
    )

    return trading_graph
