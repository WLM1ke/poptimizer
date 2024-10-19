import asyncio
import random
from datetime import timedelta
from typing import Final

from poptimizer.domain.entity.dl import datasets, risk
from poptimizer.domain.entity.dl.wave_net import backbone
from poptimizer.domain.service import view
from poptimizer.domain.service.dl import builder, trainer
from poptimizer.service.common import logging
from poptimizer.service.fsm import states

_NEW_FORECAST_PROBABILITY: Final = 0.1
_STEP_DURATION: Final = timedelta(hours=1)

_DESC: Final = trainer.DLModel(
    batch=trainer.Batch(
        size=320,
        feats=builder.Features(
            close=True,
            div=True,
            ret=True,
        ),
        days=datasets.Days(
            history=252,
            forecast=21,
            test=64,
        ),
    ),
    net=backbone.Cfg(
        use_bn=True,
        sub_blocks=1,
        kernels=32,
        residual_channels=32,
        gate_channels=32,
        skip_channels=32,
        head_channels=32,
        mixture_size=4,
    ),
    optimizer=trainer.Optimizer(),
    scheduler=trainer.Scheduler(epochs=3, max_lr=0.0015),
    utility=risk.Cfg(risk_tolerance=0.5),
)


class EvolutionAction:
    def __init__(self, lgr: logging.Service, view_service: view.Service) -> None:
        self._lgr = lgr
        self._view_service = view_service

    async def __call__(self) -> states.States:
        await asyncio.sleep(_STEP_DURATION.total_seconds())

        last_day = await self._view_service.last_day()
        tickers = await self._view_service.portfolio_tickers()
        tr = trainer.Trainer(self._lgr, builder.Builder(self._view_service))
        await tr.run(tickers, last_day, _DESC, None)

        match random.random() < _NEW_FORECAST_PROBABILITY:  # noqa: S311
            case True:
                return states.States.OPTIMIZATION
            case False:
                return states.States.DATA_UPDATE
