from poptimizer.core import fsm
from poptimizer.data.events import DataUpdated, DayNotChanged
from poptimizer.evolve import actions, events
from poptimizer.evolve.dl import builder
from poptimizer.evolve.dl.trainer import Trainer
from poptimizer.fsm import graph


def build_graph() -> graph.Graph:
    trainer = Trainer(builder.Builder())

    data_graph = graph.Graph("EvolveFSM")

    data_graph.add_state(
        fsm.AppStopped,
        [(DataUpdated, actions.InitEvolutionAction())],
    )
    data_graph.add_state(
        DataUpdated,
        [
            (events.BaseModelNotEvaluated, actions.EvaluateBaseModelAction(trainer)),
            (events.NewModelCreated, actions.EvaluateNewModelAction(trainer)),
        ],
    )
    data_graph.add_state(
        events.BaseModelNotEvaluated,
        [
            (events.NewModelCreated, actions.EvaluateNewModelAction(trainer)),
            (events.BaseModelNotEvaluated, actions.EvaluateBaseModelAction(trainer)),
        ],
    )
    data_graph.add_state(
        events.NewModelCreated,
        [
            (events.NewModelCreated, actions.EvaluateNewModelAction(trainer)),
            (events.BaseModelNotEvaluated, actions.EvaluateBaseModelAction(trainer)),
            events.ModelDeleted,
        ],
    )
    data_graph.add_state(
        events.ModelDeleted,
        [
            (DayNotChanged, actions.EvaluateExistingModelAction(trainer)),
            (DataUpdated, actions.InitEvolutionAction()),
        ],
    )
    data_graph.add_state(
        DayNotChanged,
        [
            (events.NewModelCreated, actions.EvaluateNewModelAction(trainer)),
            (events.BaseModelNotEvaluated, actions.EvaluateBaseModelAction(trainer)),
            events.ModelDeleted,
        ],
    )

    return data_graph
