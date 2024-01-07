from typing import Final

from poptimizer.adapters import message
from poptimizer.core import domain
from poptimizer.portfolio import portfolio, requests

_PORTFOLIO: Final = domain.Subdomain("portfolio")


def init_subdomain(
    bus: message.Bus,
) -> None:
    bus.add_event_handler(
        _PORTFOLIO,
        portfolio.PortfolioEventHandler(),
        message.IndefiniteRetryPolicy,
    )
    bus.add_request_handler(
        _PORTFOLIO,
        requests.PortfolioDataRequestHandler(),
    )
