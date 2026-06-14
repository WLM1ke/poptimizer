from poptimizer.forecast.events import ForecastUpdated
from poptimizer.fsm import graph
from poptimizer.trading import actions, events


def build_graph(tinkoff_client: actions.TinkoffClient) -> graph.Graph:
    trading_graph = graph.Graph("TradingFSM")

    trading_graph.add_state(
        events.TradingPaused,
        [
            graph.Transition(
                on=ForecastUpdated,
                action=actions.CheckMarketStateAction(),
                dst=events.TradingPaused,
            ),
            graph.Transition(
                on=events.TradingDayChanged,
                action=actions.InitTradingDayAction(),
                dst=events.TradingPaused,
            ),
            graph.Transition(
                on=events.MarketClosed,
                dst=events.TradingPaused,
            ),
            graph.Transition(
                on=events.MarketOpened,
                action=actions.CancelObsoleteOrdersAction(),
                dst=events.MarketOpened,
            ),
        ],
    )

    trading_graph.add_state(
        events.MarketOpened,
        [
            graph.Transition(
                on=events.ObsoleteOrdersCanceled,
                action=actions.SubmitBuyOrdersAction(),
                dst=events.ObsoleteOrdersCanceled,
            ),
        ],
    )

    trading_graph.add_state(
        events.ObsoleteOrdersCanceled,
        [
            graph.Transition(
                on=events.FreeCashLeft,
                dst=events.TradingPaused,
            ),
            graph.Transition(
                on=events.BuyOrdersSubmitted,
                action=actions.SubmitSellOrdersAction(),
                dst=events.BuyOrdersSubmitted,
            ),
        ],
    )

    trading_graph.add_state(
        events.BuyOrdersSubmitted,
        [
            graph.Transition(
                on=events.SellOrdersSubmitted,
                dst=events.TradingPaused,
            ),
        ],
    )

    return trading_graph
