import asyncio
from datetime import timedelta
from typing import Final

from poptimizer.app import states

_OPTIMIZATION_DURATION: Final = timedelta(minutes=1)


class OptimizationAction:
    async def __call__(self) -> states.States:
        await asyncio.sleep(_OPTIMIZATION_DURATION.total_seconds())

        return states.States.EVOLUTION_STEP
