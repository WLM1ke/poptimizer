import asyncio
import contextlib
from collections.abc import Coroutine
from typing import Any

import uvloop

from poptimizer import config
from poptimizer.adapter import adapter, http, lgr, mongo, telegram
from poptimizer.domain.entity.data.div import raw
from poptimizer.domain.service import view
from poptimizer.service import app
from poptimizer.service.common import backup, logging, uow
from poptimizer.ui import server


async def _run() -> None:
    cfg = config.Cfg()
    logger = lgr.init()
    err: Exception | None = None

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

        lgr_service = await stack.enter_async_context(logging.Service(logger, telegram_client))

        div_raw_collection: mongo.MongoCollection = mongo_db[adapter.get_component_name(raw.DivRaw)]
        backup_srv = backup.Service(lgr_service, div_raw_collection)
        await backup_srv.restore()

        ctx_factory = uow.CtxFactory(
            lgr_service,
            mongo_repo,
            view.Service(mongo_repo),
        )

        tg = asyncio.TaskGroup()
        service_coro: tuple[Coroutine[Any, Any, None], ...] = (
            app.run(
                lgr_service,
                http_client,
                ctx_factory,
            ),
            server.run(
                lgr_service,
                ctx_factory,
                cfg.server_url,
                lambda: backup_srv.backup_action(tg),
            ),
        )

        try:
            await _start_app(tg, service_coro)
        except asyncio.CancelledError:
            lgr_service.info("Shutdown finished")
        except Exception as exc:  # noqa: BLE001
            lgr_service.warn(f"Shutdown abnormally: {exc!r}")
            err = exc

    if err:
        raise err


async def _start_app(
    tg: asyncio.TaskGroup,
    service_coro: tuple[Coroutine[Any, Any, None], ...],
) -> None:
    async with tg:
        for coro in service_coro:
            tg.create_task(coro)


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
