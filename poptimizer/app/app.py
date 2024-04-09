import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import repo, telegram, uow
from poptimizer.app import data
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

        # Тут добавить контекстный менеджер для бекапа

        mongo_db: mongo.MongoDatabase = mongo_client[cfg.mongo_db_db]
        ctx_factory = uow.CtxFactory(
            logger,
            repo.Mongo(mongo_db),
        )

        await data.run(http_client, ctx_factory)


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
