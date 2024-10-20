import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapter import http, lgr, mongo
from poptimizer.domain.data import trading_day


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
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))
        repo = mongo.Repo(mongo_client, cfg.mongo_db_db)
        print(await repo.get(trading_day.TradingDay))


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())
