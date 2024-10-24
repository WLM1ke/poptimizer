import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import http, logger, mongo
from poptimizer.controllers.bus import bus


async def _run() -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.client())
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))

        lgr = await stack.enter_async_context(
            logger.init(
                http_client,
                cfg.telegram_token,
                cfg.telegram_chat_id,
            )
        )

        try:
            await bus.run(http_client, mongo_db)
        except asyncio.CancelledError:
            lgr.info("Shutdown finished")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
