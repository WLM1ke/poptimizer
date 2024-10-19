import asyncio
import random
from datetime import timedelta
from typing import Final

from poptimizer.domain.entity import entity
from poptimizer.domain.entity.evolve import organism
from poptimizer.domain.service import view
from poptimizer.domain.service.dl import builder, trainer
from poptimizer.service.common import logging
from poptimizer.service.fsm import states

_NEW_FORECAST_PROBABILITY: Final = 0.1
_STEP_DURATION: Final = timedelta(hours=1)


class EvolutionAction:
    def __init__(self, lgr: logging.Service, view_service: view.Service) -> None:
        self._lgr = lgr
        self._view_service = view_service

    async def __call__(self) -> states.States:
        await asyncio.sleep(_STEP_DURATION.total_seconds())

        last_day = await self._view_service.last_day()
        org = organism.Organism(
            rev=entity.Revision(uid=entity.UID("uid"), ver=entity.Version(0)),
            day=last_day.date(),
            tickers=await self._view_service.portfolio_tickers(),
        )

        cfg = trainer.Cfg.model_validate(org.phenotype)

        tr = trainer.Trainer(self._lgr, builder.Builder(self._view_service))
        await tr.run(org.tickers, last_day, cfg, None)

        match random.random() < _NEW_FORECAST_PROBABILITY:  # noqa: S311
            case True:
                return states.States.OPTIMIZATION
            case False:
                return states.States.DATA_UPDATE
