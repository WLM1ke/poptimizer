import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import http, lgr, mongo, msg, uow
from poptimizer.service import bus


async def _run() -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.client())
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))

        tg = await stack.enter_async_context(asyncio.TaskGroup())
        lgr.init(
            tg,
            http_client,
            cfg.telegram_token,
            cfg.telegram_chat_id,
        )
        repo = mongo.Repo(mongo_client, cfg.mongo_db_db)
        bus.run(
            msg.Bus(tg, repo, uow.CtxFactory()),
            http_client,
        )


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
