from typing import Final

import uvloop

from poptimizer import config
from poptimizer.adapters import lgr, message, telegram, uow
from poptimizer.core import domain
from poptimizer.data import cpi, day_started, trading_day
from poptimizer.io import http, mongo

_APP: Final = domain.Subdomain("app")
_DATA: Final = domain.Subdomain("data_new")


async def _run() -> None:
    cfg = config.Cfg()
    lgr.init(cfg.logger.level)

    async with (
        http.HTTPClient() as http_client,
        mongo.client(cfg.mongo_db.uri) as mongo_client,
        message.Bus(uow.UOWFactory(mongo_client)) as bus,
    ):
        bus.add_event_handler(
            _APP,
            telegram.ErrorEventHandler(http_client, cfg.telegram.token, cfg.telegram.chat_id),
            message.IgnoreErrorPolicy,
        )

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
        bus.add_event_publisher(day_started.DayStartedPublisher())


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
