from poptimizer.app import states


class OptimizationAction:
    async def __call__(self) -> states.States:
        return states.States.DATA_UPDATE
