from typing import Final

import uvloop

from poptimizer import config
from poptimizer.adapters import lgr, message, uow
from poptimizer.core import domain
from poptimizer.data import day_started, trading_day
from poptimizer.io import http, mongo

_SUBDOMAIN: Final = domain.Subdomain("data_new")


async def _run() -> None:
    cfg = config.Cfg()

    async with (
        http.HTTPClient(
            cfg.http_client.con_per_host,
            cfg.http_client.retries,
            cfg.http_client.first_retry,
            cfg.http_client.backoff_factor,
        ) as http_client,
        lgr.init(
            http_client,
            cfg.logger.level,
            cfg.logger.telegram_level,
            cfg.logger.telegram_token,
            cfg.logger.telegram_chat_id,
        ),
        mongo.client(cfg.mongo_client.uri) as mongo_client,
        message.Bus(uow.UOWFactory(mongo_client)) as bus,
    ):
        bus.add_event_handler(_SUBDOMAIN, trading_day.EventHandler(http_client))
        bus.add_event_publisher(day_started.Publisher())


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
