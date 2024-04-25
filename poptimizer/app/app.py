import asyncio
import contextlib
import logging

import uvloop

from poptimizer import config
from poptimizer.adapters import backup, repo, telegram, uow
from poptimizer.app import data, server
from poptimizer.core import domain
from poptimizer.data import status, view
from poptimizer.io import http, lgr, mongo


async def _run(lgr: logging.Logger, cfg: config.Cfg) -> None:
    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.HTTPClient())
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))
        tg = await stack.enter_async_context(asyncio.TaskGroup())

        telegram_client = telegram.Client(
            lgr,
            http_client,
            cfg.telegram_token,
            cfg.telegram_chat_id,
        )
        telegram_lgr = telegram.Logger(
            lgr,
            telegram_client,
            tg,
        )

        mongo_db: mongo.MongoDatabase = mongo_client[cfg.mongo_db_db]
        div_raw_collection: mongo.MongoCollection = mongo_db[domain.get_component_name(status.DivRaw)]
        backup_srv = backup.Service(telegram_lgr, div_raw_collection, tg)
        await backup_srv.restore()

        mongo_repo = repo.Mongo(mongo_db)
        viewer = view.Viewer(mongo_repo)
        ctx_factory = uow.CtxFactory(
            telegram_lgr,
            mongo_repo,
            viewer,
        )

        tg.create_task(data.run(http_client, ctx_factory))
        tg.create_task(server.run(telegram_lgr, ctx_factory, cfg.server_url, backup_srv))


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    logger = lgr.init()
    cfg = config.Cfg()

    try:
        uvloop.run(_run(logger, cfg))
    except KeyboardInterrupt:
        logger.info("Shutdown finished")
