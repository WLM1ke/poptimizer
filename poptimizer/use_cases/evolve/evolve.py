import asyncio

from poptimizer.use_cases import handler


class EvolutionHandler:
    async def __call__(
        self,
        ctx: handler.Ctx,  # noqa: ARG002
        msg: handler.DataChecked | handler.DataUpdated,  # noqa: ARG002
    ) -> handler.EvolutionStepFinished:
        await asyncio.sleep(60 * 60)
        return handler.EvolutionStepFinished()
