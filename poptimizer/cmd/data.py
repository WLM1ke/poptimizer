import contextlib
from typing import Final

import uvloop

from poptimizer import config
from poptimizer.adapters import errors, message, uow
from poptimizer.core import domain
from poptimizer.data import cpi, day_started, divs, indexes, quotes, securities, status, trading_day, usd
from poptimizer.io import http, lgr, mongo

_APP: Final = domain.Subdomain("app")
_DATA: Final = domain.Subdomain("data_new")


async def _run() -> None:
    cfg = config.Cfg()
    logger = lgr.init(cfg.log_level)

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.HTTPClient())
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))
        ouw_factory = uow.UOWFactory(mongo_client)
        bus = await stack.enter_async_context(message.Bus(logger, ouw_factory))

        bus.add_event_handler(
            _APP,
            errors.ErrorEventHandler(logger, http_client, cfg.telegram_token, cfg.telegram_chat_id),
            message.IgnoreErrorsPolicy,
        )

        bus.add_event_publisher(day_started.DayStartedPublisher())
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
            usd.USDEventHandler(http_client),
            message.IndefiniteRetryPolicy,
        )
        bus.add_event_handler(
            _DATA,
            divs.DividendsEventHandler(),
            message.IndefiniteRetryPolicy,
        )


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
