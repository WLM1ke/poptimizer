import asyncio

from poptimizer.use_cases import handler


class EvolutionHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.DataChecked | handler.DataUpdated) -> None:  # noqa: ARG002
        await asyncio.sleep(60 * 60)
        ctx.publish(handler.EvolutionStepFinished())
