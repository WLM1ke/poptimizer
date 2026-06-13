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
        [
            graph.Transition(
                on=DataUpdated,
                action=actions.InitEvolutionAction(),
                dst=DataUpdated,
            ),
        ],
    )
    data_graph.add_state(
        DataUpdated,
        [
            graph.Transition(
                on=events.BaseModelNotEvaluated,
                action=actions.EvaluateBaseModelAction(trainer),
                dst=events.BaseModelNotEvaluated,
            ),
            graph.Transition(
                on=events.BaseModelEvaluated,
                action=actions.EvaluateExistingModelAction(trainer),
                dst=events.BaseModelEvaluated,
            ),
            graph.Transition(
                on=events.NewModelCreated,
                action=actions.EvaluateNewModelAction(trainer),
                dst=events.NewModelCreated,
            ),
        ],
    )
    data_graph.add_state(
        events.BaseModelNotEvaluated,
        [
            graph.Transition(
                on=events.NewModelCreated,
                action=actions.EvaluateNewModelAction(trainer),
                dst=events.NewModelCreated,
            ),
            graph.Transition(
                on=events.BaseModelNotEvaluated,
                action=actions.EvaluateBaseModelAction(trainer),
                dst=events.BaseModelNotEvaluated,
            ),
        ],
    )
    data_graph.add_state(
        events.BaseModelEvaluated,
        [
            graph.Transition(
                on=events.NewModelCreated,
                action=actions.EvaluateNewModelAction(trainer),
                dst=events.NewModelCreated,
            ),
            graph.Transition(
                on=events.BaseModelNotEvaluated,
                action=actions.EvaluateBaseModelAction(trainer),
                dst=events.BaseModelNotEvaluated,
            ),
            graph.Transition(
                on=events.ModelRejected,
                dst=events.ModelRejected,
            ),
        ],
    )
    data_graph.add_state(
        events.NewModelCreated,
        [
            graph.Transition(
                on=events.NewModelCreated,
                action=actions.EvaluateNewModelAction(trainer),
                dst=events.NewModelCreated,
            ),
            graph.Transition(
                on=events.BaseModelNotEvaluated,
                action=actions.EvaluateBaseModelAction(trainer),
                dst=events.BaseModelNotEvaluated,
            ),
            graph.Transition(
                on=events.ModelRejected,
                dst=events.ModelRejected,
            ),
        ],
    )
    data_graph.add_state(
        events.ModelRejected,
        [
            graph.Transition(
                on=DayNotChanged,
                action=actions.EvaluateExistingModelAction(trainer),
                dst=DayNotChanged,
            ),
            graph.Transition(
                on=DataUpdated,
                action=actions.InitEvolutionAction(),
                dst=DataUpdated,
            ),
        ],
    )
    data_graph.add_state(
        DayNotChanged,
        [
            graph.Transition(
                on=events.NewModelCreated,
                action=actions.EvaluateNewModelAction(trainer),
                dst=events.NewModelCreated,
            ),
            graph.Transition(
                on=events.BaseModelNotEvaluated,
                action=actions.EvaluateBaseModelAction(trainer),
                dst=events.BaseModelNotEvaluated,
            ),
            graph.Transition(
                on=events.ModelRejected,
                dst=events.ModelRejected,
            ),
        ],
    )

    return data_graph
