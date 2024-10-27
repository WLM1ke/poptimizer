import asyncio

import pandas as pd

from poptimizer.domain import domain
from poptimizer.domain.evolve import organism
from poptimizer.use_cases import handler, view
from poptimizer.use_cases.dl import builder, trainer


class EvolutionHandler:
    def __init__(self, viewer: view.Viewer) -> None:
        self._viewer = viewer

    async def __call__(
        self,
        ctx: handler.Ctx,  # noqa: ARG002
        msg: handler.DataChecked | handler.DataUpdated,  # noqa: ARG002
    ) -> handler.EvolutionStepFinished:
        last_day = await self._viewer.last_day()
        org = organism.Organism(
            rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(0)),
            day=last_day,
            tickers=await self._viewer.portfolio_tickers(),
        )

        cfg = trainer.Cfg.model_validate(org.phenotype)

        tr = trainer.Trainer(builder.Builder(self._viewer))
        await tr.run(org.tickers, pd.Timestamp(last_day), cfg, None)

        await asyncio.sleep(60 * 60)

        return handler.EvolutionStepFinished()
