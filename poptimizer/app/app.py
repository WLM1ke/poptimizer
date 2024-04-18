import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import backup, repo, telegram
from poptimizer.app import data, uow
from poptimizer.core import domain
from poptimizer.data import status
from poptimizer.io import http, lgr, mongo


async def _run() -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.HTTPClient())
        logger = await stack.enter_async_context(
            telegram.Logger(
                lgr.init(),
                http_client,
                cfg.telegram_token,
                cfg.telegram_chat_id,
            ),
        )
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))
        mongo_db: mongo.MongoDatabase = mongo_client[cfg.mongo_db_db]
        div_raw_collection: mongo.MongoCollection = mongo_db[domain.get_component_name(status.DivRaw)]
        await stack.enter_async_context(backup.Backup(logger, div_raw_collection))

        ctx_factory = uow.CtxFactory(
            logger,
            repo.Mongo(mongo_db),
        )

        try:
            await data.run(http_client, ctx_factory)
        except asyncio.CancelledError:
            logger.info("Shutdown signal received")


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
