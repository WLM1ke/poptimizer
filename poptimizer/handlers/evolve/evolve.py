import asyncio

from poptimizer.handlers import handler


class EvolutionHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.DataChecked | handler.DataUpdated) -> None:  # noqa: ARG002
        await asyncio.sleep(10)
        ctx.publish(handler.EvolutionStepFinished())
