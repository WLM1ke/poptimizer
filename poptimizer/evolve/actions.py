from poptimizer.core import fsm
from poptimizer.data.events import DataUpdated
from poptimizer.evolve import events
from poptimizer.evolve.dl import trainer
from poptimizer.evolve.evolution import evolve
from poptimizer.portfolio.port import portfolio


class InitEvolutionAction:
    async def __call__(self, ctx: fsm.Ctx, event: DataUpdated) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)

        if evolution.day != event.day:
            port = await ctx.get(portfolio.Portfolio)
            evolution.init_day(port)

        match not evolution.alfa or not await ctx.count_models():
            case True:
                ctx.send(events.BaseModelNotEvaluated())
            case _:
                ctx.send(events.BaseModelEvaluated())


class EvaluateBaseModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)
        model = await ctx.get_for_update(evolve.Model, evolution.next_model)

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )

        evolution.next_model = await evolve.make_new_model(ctx, evolution, model)

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
        model = await ctx.get_for_update(evolve.Model, evolution.next_model)

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )

        match results:
            case evolve.TestResults() if await evolve.is_accepted(ctx, evolution, model, results):
                evolution.model_accepted()
                evolution.new_base(results)
                evolution.next_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.BaseModelEvaluated())
            case _ if await ctx.count_models() != 0:
                evolution.model_rejected()
                ctx.send(events.ModelRejected())
            case _:
                evolution.model_rejected()
                evolution.next_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.BaseModelNotEvaluated())


class EvaluateExistingModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)
        model = await ctx.next_model_for_update()
        evolution.next_model = model.uid

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )

        match results:
            case evolve.TestResults() if await evolve.is_accepted(ctx, evolution, model, results):
                evolution.next_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.NewModelCreated())
            case _ if await ctx.count_models() != 0:
                ctx.send(events.ModelRejected())
            case _:
                evolution.model_rejected()
                evolution.next_model = await evolve.make_new_model(ctx, evolution, model)
                ctx.send(events.BaseModelNotEvaluated())

        if results:
            evolution.new_base(results)
