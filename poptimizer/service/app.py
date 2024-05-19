import aiohttp

from poptimizer.service.common import logging, uow
from poptimizer.service.fsm import evolution, fsm, optimization, states
from poptimizer.service.fsm.data import data


async def run(
    logger: logging.Service,
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> None:
    graph = _prepare_graph(http_client, ctx_factory)
    app_fsm = fsm.FSM(logger, graph)

    await app_fsm()


def _prepare_graph(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> fsm.Graph[states.States]:
    return {
        states.States.DATA_UPDATE: {
            "action": data.UpdateDataAction(http_client, ctx_factory),
            "transitions": {
                states.States.EVOLUTION_STEP,
                states.States.OPTIMIZATION,
            },
        },
        states.States.EVOLUTION_STEP: {
            "action": evolution.EvolutionAction(),
            "transitions": {
                states.States.DATA_UPDATE,
                states.States.OPTIMIZATION,
            },
        },
        states.States.OPTIMIZATION: {
            "action": optimization.OptimizationAction(),
            "transitions": {
                states.States.EVOLUTION_STEP,
            },
        },
    }
