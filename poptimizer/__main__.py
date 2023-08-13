"""Основная точка входа для запуска приложения."""
import asyncio
import logging
from typing import Final

import uvloop

from poptimizer.app import clients, config, context, lgr, modules, pubsub

_Logger: Final = logging.getLogger("App")


async def _run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    cfg = config.Cfg()

    async with (
        clients.http(cfg.http_client) as http,
        lgr.init(http, cfg.logger),
        clients.mongo(cfg.mongo_client) as mongo,
        clients.nats(cfg.nats_client) as js,
        context.Ctx() as ctx,
    ):
        await pubsub.init(js)

        updater = modules.create_data_updater(http, mongo, js)
        ctx.create_task(updater(ctx))


def main() -> None:
    """Основная точка входа для запуска приложения."""
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(coro=_run())


if __name__ == "__main__":
    main()
