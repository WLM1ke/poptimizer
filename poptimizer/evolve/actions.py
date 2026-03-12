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
            evolution.init_new_day(port)

        match len(evolution.alfa):
            case 0:
                ctx.send(events.BaseModelNotEvaluated())
            case _:
                await ctx.get(evolve.Model, evolution.next_model)

                ctx.send(events.NewModelCreated())


class EvaluateBaseModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)
        model = await ctx.get(evolve.Model, evolution.next_model)

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )
        evolution.alfa = results.alfa
        evolution.llh = results.llh

        await evolve.make_new_model(ctx, evolution, model)

        ctx.send(events.NewModelCreated())


class EvaluateNewModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)
        model = await ctx.get(evolve.Model, evolution.next_model)

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )

        match await evolve.is_deleted(ctx, evolution, model, results):
            case True if await ctx.count_models() >= 1:
                evolution.model_rejected()
                evolution.next_model = await ctx.next_model()
                ctx.send(events.ModelDeleted())
            case True:
                evolution.model_rejected()
                ctx.send(events.NoModelsLeft())
            case False:
                evolution.model_accepted()
                evolution.new_base(results)
                await evolve.make_new_model(ctx, evolution, model)

                ctx.send(events.NewModelCreated())


class EvaluateExistingModelAction:
    def __init__(self, trainer: trainer.Trainer) -> None:
        self._trainer = trainer

    async def __call__(self, ctx: fsm.Ctx) -> None:
        evolution = await ctx.get_for_update(evolve.Evolution)
        model = await ctx.get(evolve.Model, evolution.next_model)

        results = await self._trainer.update_model_metrics(
            ctx,
            evolution,
            model,
        )

        evolution.new_base(results)
        await evolve.is_deleted(ctx, evolution, model, results)
        await evolve.make_new_model(ctx, evolution, model)
        ctx.send(events.NewModelCreated())
