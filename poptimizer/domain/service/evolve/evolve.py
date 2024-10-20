import bson

from poptimizer.domain.entity_ import entity
from poptimizer.domain.entity_.evolve import evolve, organism
from poptimizer.domain.service import domain_service, view


class Evolution:
    def __init__(self, view_service: view.Service) -> None:
        self._view_service = view_service

    async def __call__(self, ctx: domain_service.Ctx) -> None:
        state = await ctx.get(evolve.Evolution)
        if not state.ver:
            await self._setup(ctx, state)

    async def _setup(self, ctx: domain_service.Ctx, state: evolve.Evolution) -> None:
        state.day = await self._view_service.last_day()
        uid = entity.UID(str(bson.ObjectId()))
        await ctx.get(organism.Organism, uid)
