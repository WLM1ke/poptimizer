import asyncio
import logging

import pandas as pd

from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve, organism
from poptimizer.use_cases import handler, view
from poptimizer.use_cases.dl import builder, trainer


class EvolutionHandler:
    def __init__(self, viewer: view.Viewer) -> None:
        self._lgr = logging.getLogger()
        self._viewer = viewer

    async def __call__(
        self,
        ctx: handler.Ctx,
        msg: handler.DataNotChanged | handler.DataUpdated,
    ) -> handler.EvolutionStepFinished:
        evolution = await self._init_step(ctx, msg.day)

        org = organism.Organism(
            rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(0)),
            day=evolution.day,
            tickers=evolution.tickers,
        )

        cfg = trainer.Cfg.model_validate(org.phenotype)

        tr = trainer.Trainer(builder.Builder(self._viewer))
        await tr.run(org.tickers, pd.Timestamp(evolution.day), cfg, None)

        # await asyncio.sleep(60 * 60)

        return handler.EvolutionStepFinished()

    async def _init_step(self, ctx: handler.Ctx, day: domain.Day) -> evolve.Evolution:
        evolution = await ctx.get_for_update(evolve.Evolution)
        evolution.tickers = await self._viewer.portfolio_tickers()

        match evolution.ver:
            case 0:
                evolution.day = day
            # Должна быть проверка, что всех переучили
            case _ if day > evolution.day:
                evolution.day = day
                evolution.step = 1
            case _:
                evolution.step += 1

        self._lgr.info("Evolution step %d for %s", evolution.step, evolution.day)

        return evolution
