import contextlib
from typing import Final

import uvloop

from poptimizer import config
from poptimizer.adapters import errors, message, uow
from poptimizer.app import data, portfolio
from poptimizer.core import domain
from poptimizer.io import http, lgr, mongo

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
            errors.ErrorEventHandler(logger, http_client, cfg.telegram_token, cfg.telegram_chat_id),
            message.IgnoreErrorsPolicy,
        )
        data.init_subdomain(bus, http_client)
        portfolio.init_subdomain(bus)


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
