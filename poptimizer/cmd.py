import asyncio

import uvloop

from poptimizer import config
from poptimizer.adapters import events, uow
from poptimizer.core import domain, handlers
from poptimizer.io import mongo


class SomeEntity(domain.Entity):
    value: int = 0


class SomeEvent(domain.Event):
    ...


class EventHandler:
    def __init__(self) -> None:
        self._counter = 0

    async def handle(self, ctx: handlers.Ctx, event: SomeEvent) -> None:
        entity = await ctx.get(SomeEntity, "aaa")
        entity.value += 1
        print(entity.value)
        if self._counter < 10:
            self._counter += 1
            ctx.publish(SomeEvent())


class EventHandler2:
    async def handle(self, ctx: handlers.Ctx, event: SomeEvent) -> None:
        entity = await ctx.get(SomeEntity, "aaa", for_update=False)
        entity.value *= entity.value
        print(entity.value)


async def _run() -> None:
    cfg = config.Cfg()
    async with (
        mongo.client(cfg.mongo_client.uri) as mongo_client,
        events.Bus(uow.UOWFactory(mongo_client)) as bus,
    ):
        bus.add_event_handler("test", EventHandler())
        bus.add_event_handler("test", EventHandler2())
        bus.publish(SomeEvent())


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(coro=_run())
