import statistics

from poptimizer.core import errors, fsm
from poptimizer.evolve.dl import builder, datasets, training
from poptimizer.evolve.models import evolve


class Trainer:
    def __init__(self, runner: training.TrainingRunner, builder: builder.Builder) -> None:
        self._runner = runner
        self._builder = builder

    async def update_model_metrics(
        self,
        ctx: fsm.Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> evolve.TestResults | None:
        prefix = ""
        if model.day != evolution.day:
            prefix = "outdated "

        new = not model.mean
        if new:
            prefix = "new "

        ctx.info(
            "Day %s step %d models %d radius %.2f - %s%s",
            evolution.day,
            evolution.step,
            await ctx.count_models(),
            evolution.radius,
            prefix,
            model,
        )

        evolution.step += 1
        model.day = evolution.day

        retry = True

        while retry:
            try:
                return await self._evaluate(ctx, evolution, model)
            except* errors.POError as err:
                root_error = errors.get_root_poptimizer_error(err)
                if new or not self._retry_root_error(ctx, evolution, root_error):
                    await ctx.delete(model)
                    ctx.info(f"{model} deleted with {root_error!r}")
                    retry = False

        return None

    async def _evaluate(
        self,
        ctx: fsm.Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> evolve.TestResults:
        batch = builder.Batch.model_validate(model.phenotype["batch"])
        days = datasets.Days(
            history=batch.history_days,
            forecast=evolution.forecast_days,
            test=int(evolution.test_days),
        )
        tickers_data, emb_size, emb_seq_size = await self._builder.build(
            ctx,
            evolution.day,
            evolution.tickers,
            days,
            batch,
        )

        result = await self._runner(
            training.TrainingJob(model=model, evolution=evolution),
            training.TrainingData(
                tickers_data=tickers_data,
                emb_size=emb_size,
                emb_seq_size=emb_seq_size,
            ),
        )

        model.mean = result.forecast.mean
        model.cov = result.forecast.cov
        model.alfa = result.test.alfa
        model.llh = statistics.mean(result.test.llh)
        model.duration = result.duration

        return result.test

    def _retry_root_error(
        self,
        ctx: fsm.Ctx,
        evolution: evolve.Evolution,
        err: errors.POError,
    ) -> bool:
        if not isinstance(err, errors.TooShortHistoryError):
            return False

        if err.minimal_returns_days > evolution.minimal_returns_days:
            evolution.minimal_returns_days = err.minimal_returns_days
            ctx.warning("Minimal return days increased - %d", evolution.minimal_returns_days)

        if evolution.test_days == evolve.MINIMAL_TEST_DAYS:
            return False

        evolution.test_days = max(evolve.MINIMAL_TEST_DAYS, evolution.test_days - 1)
        ctx.warning("Test days reset - %d", int(evolution.test_days))

        return True
