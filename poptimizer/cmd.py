import asyncio

import uvloop

from poptimizer import config
from poptimizer.adapters.uow import MongoUOW
from poptimizer.core import domain, errors
from poptimizer.io import mongo


class SomeEntity(domain.BaseEntity):
    value: int = 0


async def _run() -> None:
    cfg = config.Cfg()
    async with (
        mongo.client(cfg.mongo_client.uri) as mongo_client,
        MongoUOW(mongo_client, "test", errors.POError) as uow,
    ):
        agg1 = await uow.get(SomeEntity, "aaa", for_update=False)
        agg1.value = 111

        agg2 = await uow.get(SomeEntity, "bbb")
        agg2.value = 42

        agg2 = await uow.get(SomeEntity, "bbb")
        agg2.value = 1111


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(coro=_run())
