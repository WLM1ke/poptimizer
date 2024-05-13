import aiohttp

from poptimizer.adapter import telegram
from poptimizer.adapters import fsm
from poptimizer.app import evolution, optimization
from poptimizer.service import data, states, uow


def prepare(
    logger: telegram.Logger,
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> fsm.FSM[states.States]:
    graph = _prepare_graph(http_client, ctx_factory)

    return fsm.FSM(logger, graph)


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
