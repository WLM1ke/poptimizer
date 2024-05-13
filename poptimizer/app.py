import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapter import adapter, http, lgr, mongo, telegram
from poptimizer.domain.entity import div_raw
from poptimizer.domain.service import view
from poptimizer.service import backup, logging, uow


async def _run() -> None:
    cfg = config.Cfg()
    logger = lgr.init()

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.Client())
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))
        telegram_client = telegram.Client(
            logger,
            http_client,
            cfg.telegram_token,
            cfg.telegram_chat_id,
        )
        mongo_db: mongo.MongoDatabase = mongo_client[cfg.mongo_db_db]
        mongo_repo = mongo.Repo(mongo_db)

        logging_service = await stack.enter_async_context(logging.Service(logger, telegram_client))

        div_raw_collection: mongo.MongoCollection = mongo_db[adapter.get_component_name(div_raw.DivRaw)]
        backup_srv = backup.Service(logging_service, div_raw_collection)
        await backup_srv.restore()

        ctx_factory = uow.CtxFactory(
            logging_service,
            mongo_repo,
            view.Service(mongo_repo),
        )

        # app_fsm = fsm.prepare(telegram_lgr, http_client, ctx_factory)
        tg.create_task(app_fsm())
        # tg.create_task(server.run(telegram_lgr, ctx_factory, cfg.server_url, backup_srv))


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
