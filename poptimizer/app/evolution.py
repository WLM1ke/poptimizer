import asyncio
import random
from datetime import timedelta
from typing import Final

from poptimizer.app import states

_NEW_FORECAST_PROBABILITY: Final = 0.1
_STEP_DURATION: Final = timedelta(minutes=10)


class EvolutionAction:
    async def __call__(self) -> states.States:
        await asyncio.sleep(_STEP_DURATION.total_seconds())

        match random.random() < _NEW_FORECAST_PROBABILITY:  # noqa: S311
            case True:
                return states.States.OPTIMIZATION
            case False:
                return states.States.DATA_UPDATE
