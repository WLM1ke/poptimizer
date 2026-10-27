from typing import Final

from poptimizer.core import fsm
from poptimizer.data.events import DataUpdated
from poptimizer.evolve import events
from poptimizer.evolve.dl import trainer
from poptimizer.evolve.models import evolve
from poptimizer.portfolio.models import portfolio

_DAY_IN_SECONDS: Final = 24 * 60 * 60
_MIN_DURATION: Final = 1e-9


class InitEvolutionAction:
    async def __call__(self, ctx: fsm.Ctx, event: DataUpdated) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)

        if evolution.day != event.day:
            port = await ctx.get(portfolio.Portfolio)
            evolution.init_day(port)

        match not evolution.llh or not await ctx.count_models():
            case True:
                ctx.send(events.BaseModelNotEvaluated())
            case _:
                ctx.send(events.BaseModelEvaluated())


class EvaluateBaseModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)
        model = await ctx.get_for_update(evolve.Model, evolution.previous_model)

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )

        evolution.previous_model = await evolve.make_new_model(ctx, evolution, model)

        if not results:
            ctx.send(events.BaseModelNotEvaluated())

            return

        evolution.new_base(results)
        ctx.send(events.NewModelCreated())


class EvaluateNewModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)
        model = await ctx.get_for_update(evolve.Model, evolution.previous_model)

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )

        match results:
            case evolve.TestResults() if await evolve.is_accepted(ctx, evolution, model, results):
                evolution.model_accepted()
                evolution.new_base(results)
                evolution.previous_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.NewModelCreated())
            case _ if await ctx.count_models() != 0:
                evolution.model_rejected()
                ctx.send(events.ModelRejected())
            case _:
                evolution.model_rejected()
                evolution.previous_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.BaseModelNotEvaluated())


class EvaluateExistingModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)

        if await ctx.count_models() > evolution.cnt:
            worst_count = await ctx.delete_worst_model()
            ctx.warning("Deleting %d worst models", worst_count)

        model, longest_duration = await ctx.next_model_for_update()

        results: evolve.TestResults | None = None

        if _is_slow_outdated(evolution, model):
            await ctx.delete(model)
            ctx.warning("Deleting slow outdated model - %s", model)
        else:
            evolution.previous_model = model.uid
            _move_target_count(evolution, model, longest_duration)

            results = await self._trainer.update_model_metrics(ctx, evolution, model)

        match results:
            case evolve.TestResults() if await evolve.is_accepted(ctx, evolution, model, results):
                evolution.previous_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.NewModelCreated())
            case _ if await ctx.count_models() != 0:
                ctx.send(events.ModelRejected())
            case _:
                evolution.model_rejected()
                evolution.previous_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.BaseModelNotEvaluated())

        if results:
            evolution.new_base(results)


def _is_slow_outdated(evolution: evolve.Evolution, model: evolve.Model) -> bool:
    return model.day != evolution.day and model.duration * evolution.cnt > _DAY_IN_SECONDS


def _move_target_count(evolution: evolve.Evolution, model: evolve.Model, longest_duration: float) -> None:
    if model.day != evolution.day:
        return

    per_day = _DAY_IN_SECONDS / max(longest_duration, _MIN_DURATION)

    if evolution.cnt < per_day:
        evolution.cnt += 1
    elif evolution.cnt > 1:
        evolution.cnt -= 1
