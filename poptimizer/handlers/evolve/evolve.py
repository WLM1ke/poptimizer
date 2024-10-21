import asyncio

from poptimizer.handlers import handler


class EvolutionHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.DataUpdateFinished) -> None:
        await asyncio.sleep(3)
        ctx.publish(handler.NewDataCheckRequired(day=msg.day))
