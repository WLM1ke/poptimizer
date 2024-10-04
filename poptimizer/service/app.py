import aiohttp

from poptimizer.domain.service import view
from poptimizer.service.common import logging, uow
from poptimizer.service.fsm import evolution, fsm, optimization, states
from poptimizer.service.fsm.data import data


async def run(
    logger: logging.Service,
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
    view_service: view.Service,
) -> None:
    graph = _prepare_graph(http_client, ctx_factory, view_service)
    app_fsm = fsm.FSM(logger, graph)

    await app_fsm()


def _prepare_graph(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
    view_service: view.Service,
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
            "action": evolution.EvolutionAction(view_service),
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
