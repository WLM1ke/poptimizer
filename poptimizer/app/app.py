import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import backup, repo, telegram
from poptimizer.app import data, server, uow
from poptimizer.core import domain
from poptimizer.data import status, view
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

        mongo_repo = repo.Mongo(mongo_db)
        viewer = view.Viewer(mongo_repo)
        ctx_factory = uow.CtxFactory(
            logger,
            mongo_repo,
            viewer,
        )

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(data.run(http_client, ctx_factory))
                tg.create_task(server.run(ctx_factory, cfg.server_url))
        except asyncio.CancelledError:
            logger.info("Shutdown finished")


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
