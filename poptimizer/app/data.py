from typing import Final

import aiohttp

from poptimizer.adapters import message
from poptimizer.core import domain
from poptimizer.data import cpi, day_started, divs, indexes, quotes, raw, requests, securities, status, trading_day, usd

_DATA: Final = domain.Subdomain("data_new")


def init_subdomain(
    bus: message.Bus,
    http_client: aiohttp.ClientSession,
) -> None:
    bus.add_service(day_started.DayStartedService())
    bus.add_event_handler(
        _DATA,
        trading_day.TradingDayEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        _DATA,
        cpi.CPIEventHandler(http_client),
        message.IgnoreErrorsPolicy,
    )
    bus.add_event_handler(
        _DATA,
        indexes.IndexesEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        _DATA,
        securities.SecuritiesEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        _DATA,
        quotes.QuotesEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        _DATA,
        status.DivStatusEventHandler(http_client),
        message.IgnoreErrorsPolicy,
    )
    bus.add_event_handler(
        _DATA,
        raw.CheckRawDividendsEventHandler(),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        _DATA,
        usd.USDEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        _DATA,
        divs.DividendsEventHandler(),
        message.IndefiniteRetryPolicy,
    )
    bus.add_request_handler(
        _DATA,
        requests.SecDataRequestHandler(),
    )
