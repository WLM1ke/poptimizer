from poptimizer.forecast.events import ForecastUpdated
from poptimizer.fsm import graph
from poptimizer.portfolio.events import PortfolioRevalued
from poptimizer.trading import actions, events


def build_graph() -> graph.Graph:
    trading_graph = graph.Graph("TradingFSM")

    trading_graph.add_state(
        events.ReadyForTrading,
        [
            graph.Transition(
                on=PortfolioRevalued,
                action=actions.InitTradingStateAction(),
                dst=events.ReadyForTrading,
            ),
            graph.Transition(
                on=ForecastUpdated,
                action=actions.CancelStaleOrdersAction(),
                dst=events.ReadyForTrading,
            ),
        ],
    )

    return trading_graph
