import asyncio
import logging
from typing import Final, Protocol

import bson
import pandas as pd

from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve, organism
from poptimizer.use_cases import handler, view
from poptimizer.use_cases.dl import builder, trainer

_DIF_PARENTS_COUNT: Final = 2


def random_org_uid() -> domain.UID:
    return domain.UID(str(bson.ObjectId()))


class Ctx(Protocol):
    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def next_org(self) -> organism.Organism: ...

    async def sample_orgs(self, n: int) -> list[organism.Organism]: ...


class EvolutionHandler:
    def __init__(self, viewer: view.Viewer) -> None:
        self._lgr = logging.getLogger()
        self._viewer = viewer

    async def __call__(
        self,
        ctx: Ctx,
        msg: handler.DataNotChanged | handler.DataUpdated,
    ) -> handler.EvolutionStepFinished:
        evolution = await self._init_step(ctx, msg.day)

        org = await ctx.next_org()
        org = await self._make_child(ctx, org)

        cfg = trainer.Cfg.model_validate(org.phenotype)

        tr = trainer.Trainer(builder.Builder(self._viewer))
        await tr.run(evolution.tickers, pd.Timestamp(evolution.day), cfg, None)
        org.tickers = evolution.tickers
        org.day = evolution.day

        await asyncio.sleep(60 * 60)

        return handler.EvolutionStepFinished()

    async def _init_step(self, ctx: handler.Ctx, day: domain.Day) -> evolve.Evolution:
        evolution = await ctx.get_for_update(evolve.Evolution)
        evolution.tickers = await self._viewer.portfolio_tickers()

        match evolution.ver:
            case 0:
                evolution.day = day
                await ctx.get_for_update(organism.Organism, random_org_uid())
            # Должна быть проверка, что всех переучили
            case _ if day > evolution.day:
                evolution.day = day
                evolution.step = 1
            case _:
                evolution.step += 1

        self._lgr.info("Evolution step %d for %s", evolution.step, evolution.day)

        return evolution

    async def _make_child(self, ctx: Ctx, org: organism.Organism) -> organism.Organism:
        parents = await ctx.sample_orgs(2)
        if len(parents) != _DIF_PARENTS_COUNT or parents[0].uid == parents[1].uid:
            parents = [organism.Organism(day=org.day, rev=org.rev), organism.Organism(day=org.day, rev=org.rev)]

        child = await ctx.get_for_update(organism.Organism, random_org_uid())
        child.genes = org.make_child_genes(parents[0], parents[1], 1)

        return child
