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
        evolution, org = await self._init_step(ctx, msg.day)
        self._lgr.info("Evolution step %d for %s", evolution.step, evolution.day)

        self._lgr.info("Train parent")
        org = await self._eval(org, evolution.day, evolution.tickers)
        evolution.prev_org_uid = org.uid

        self._lgr.info("Train child")
        await self._eval(await self._make_child(ctx, org), evolution.day, evolution.tickers)

        await asyncio.sleep(60 * 60)

        return handler.EvolutionStepFinished()

    async def _init_step(self, ctx: Ctx, day: domain.Day) -> tuple[evolve.Evolution, organism.Organism]:
        evolution = await ctx.get_for_update(evolve.Evolution)
        if evolution.ver == 0:
            await ctx.get_for_update(organism.Organism, random_org_uid())

        if evolution.day != day and day not in evolution.next_days:
            evolution.next_days.append(day)
            evolution.tickers = await self._viewer.portfolio_tickers()

        org = await ctx.next_org()

        match evolution.next_days:
            case [next_day, *rest] if org.day == evolution.day:
                evolution.day = next_day
                evolution.next_days = rest
                evolution.step = 1
            case _:
                evolution.step += 1

        return evolution, org

    async def _make_child(self, ctx: Ctx, org: organism.Organism) -> organism.Organism:
        parents = await ctx.sample_orgs(2)
        if len(parents) != _DIF_PARENTS_COUNT or parents[0].uid == parents[1].uid:
            parents = [organism.Organism(day=org.day, rev=org.rev), organism.Organism(day=org.day, rev=org.rev)]

        child = await ctx.get_for_update(organism.Organism, random_org_uid())
        child.genes = org.make_child_genes(parents[0], parents[1], 1)

        return child

    async def _eval(
        self,
        org: organism.Organism,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
    ) -> organism.Organism:
        cfg = trainer.Cfg.model_validate(org.phenotype)

        tr = trainer.Trainer(builder.Builder(self._viewer))
        await tr.run(tickers, pd.Timestamp(day), cfg, None)
        org.tickers = tickers
        org.day = day

        return org
