from typing import Final

import aiohttp

from poptimizer.adapters import message
from poptimizer.core import domain
from poptimizer.data import (
    cpi,
    day_started,
    divs,
    indexes,
    quotes,
    reestry,
    requests,
    securities,
    status,
    trading_day,
    usd,
)

DATA: Final = domain.Subdomain("data_new")


def init_subdomain(
    bus: message.Bus,
    http_client: aiohttp.ClientSession,
) -> None:
    bus.add_service(day_started.DayStartedService())
    bus.add_event_handler(
        DATA,
        trading_day.TradingDayEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        DATA,
        cpi.CPIEventHandler(http_client),
        message.IgnoreErrorsPolicy,
    )
    bus.add_event_handler(
        DATA,
        indexes.IndexesEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        DATA,
        securities.SecuritiesEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        DATA,
        quotes.QuotesEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        DATA,
        status.DivStatusEventHandler(http_client),
        message.IgnoreErrorsPolicy,
    )
    bus.add_event_handler(
        DATA,
        reestry.ReestryDividendsEventHandler(http_client),
        message.IgnoreErrorsPolicy,
    )
    bus.add_event_handler(
        DATA,
        usd.USDEventHandler(http_client),
        message.IndefiniteRetryPolicy,
    )
    bus.add_event_handler(
        DATA,
        divs.DividendsEventHandler(),
        message.IndefiniteRetryPolicy,
    )
    bus.add_request_handler(
        DATA,
        requests.SecDataRequestHandler(),
    )

    bus.add_request_handler(
        DATA,
        requests.DivTickersRequestHandler(),
    )
    bus.add_request_handler(
        DATA,
        requests.GetDividendsRequestHandler(),
    )
    bus.add_request_handler(
        DATA,
        requests.UpdateDividendsRequestHandler(),
    )
