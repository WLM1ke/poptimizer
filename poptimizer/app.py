import asyncio
import contextlib
import logging

import uvloop

from poptimizer import config
from poptimizer.adapter import http, lgr


async def _run() -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.client())
        tg = await stack.enter_async_context(asyncio.TaskGroup())
        lgr.init(
            tg,
            http_client,
            cfg.telegram_token,
            cfg.telegram_chat_id,
        )
        logging.info("info")
        logging.warning("warn")


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
