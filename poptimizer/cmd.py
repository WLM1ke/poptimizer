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
    async def handle(self, ctx: handlers.Ctx, event: SomeEvent) -> None:
        entity = await ctx.get(SomeEntity, "aaa")
        entity.value -= 1
        print(entity.value)
        if entity.value > 0:
            ctx.publish(SomeEvent())


class SomeResponse(domain.Response):
    qqq: int


class SomeRequest(domain.Request[SomeResponse]):
    value: int


class RequestHandler:
    async def handle(self, ctx: handlers.Ctx, request: SomeRequest) -> SomeResponse:
        entity = await ctx.get(SomeEntity, "aaa")
        entity.value = request.value**2

        ctx.publish(SomeEvent())

        return SomeResponse(qqq=request.value**2)


async def _run() -> None:
    cfg = config.Cfg()
    async with (
        mongo.client(cfg.mongo_client.uri) as mongo_client,
        events.Bus(uow.UOWFactory(mongo_client)) as bus,
    ):
        bus.add_event_handler("test", EventHandler())
        bus.add_request_handler("test", RequestHandler())

        a = await bus.request(SomeRequest(value=2))

        print(a.qqq)


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        runner.run(coro=_run())
