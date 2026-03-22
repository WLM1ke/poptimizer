from poptimizer.forecast import actions, events
from poptimizer.fsm import graph
from poptimizer.portfolio.events import PortfolioRevalued, PositionChecked


def build_graph() -> graph.Graph:
    data_graph = graph.Graph("ForecastFSM")

    data_graph.add_state(
        events.ForecastUpdated,
        [
            (PortfolioRevalued, actions.InitForecastAction(), events.ForecastUpdated),
            (PositionChecked, actions.UpdateForecastAction(), events.ForecastUpdated),
        ],
    )

    return data_graph
