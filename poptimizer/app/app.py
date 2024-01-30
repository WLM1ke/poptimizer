import contextlib
from typing import Final

import uvloop

from poptimizer import config
from poptimizer.adapters import backup, message, uow, warn
from poptimizer.app import data, portfolio
from poptimizer.core import domain
from poptimizer.data import status
from poptimizer.io import http, lgr, mongo
from poptimizer.ui import server

_APP: Final = domain.Subdomain("app")


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
            warn.WarningEventHandler(logger, http_client, cfg.telegram_token, cfg.telegram_chat_id),
            message.IgnoreErrorsPolicy,
        )
        raw_div_db: mongo.MongoDatabase = mongo_client[data.DATA]
        raw_div_collection: mongo.MongoCollection = raw_div_db[domain.get_component_name_for_type(status.DivRaw)]
        bus.add_event_handler(
            _APP,
            backup.DivBackupEventHandler(raw_div_collection),
            message.IgnoreErrorsPolicy,
        )
        data.init_subdomain(bus, http_client)
        portfolio.init_subdomain(bus)
        bus.add_service(server.APIServerService(cfg.server_url))


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
