import contextlib
from typing import Final

import uvloop

from poptimizer import config
from poptimizer.adapters import lgr, message, uow
from poptimizer.core import domain
from poptimizer.data import cpi, day_started, trading_day
from poptimizer.io import http, mongo, telegram

_APP: Final = domain.Subdomain("app")
_DATA: Final = domain.Subdomain("data_new")


async def _run() -> None:
    cfg = config.Cfg()
    logger = lgr.init(cfg.log_level)

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.HTTPClient())
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))
        telegram_client = telegram.Client(logger, http_client, cfg.telegram_token, cfg.telegram_chat_id)
        ouw_factory = uow.UOWFactory(mongo_client)
        bus = await stack.enter_async_context(message.Bus(logger, telegram_client, ouw_factory))

        bus.add_event_publisher(day_started.DayStartedPublisher())
        bus.add_event_handler(
            _DATA,
            trading_day.TradingDayEventHandler(http_client),
            message.IndefiniteRetryPolicy,
        )
        bus.add_event_handler(
            _DATA,
            cpi.CPIEventHandler(http_client),
            message.IgnoreErrorPolicy,
        )


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
