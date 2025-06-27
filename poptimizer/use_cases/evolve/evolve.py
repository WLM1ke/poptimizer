import logging
import operator
import statistics
from typing import Final, Protocol, Self

import bson
from pydantic import BaseModel, FiniteFloat, PositiveInt

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler
from poptimizer.use_cases.dl import builder, trainer

_PARENT_COUNT: Final = 2
_CRITICAL_FACTOR: Final = 0.01


def _random_uid() -> domain.UID:
    return domain.UID(str(bson.ObjectId()))


def _extract_minimal_returns_days(err_group: BaseExceptionGroup[errors.DomainError]) -> int | None:
    if (subgroup := err_group.subgroup(errors.TooShortHistoryError)) is None:
        return None

    while True:
        if isinstance(subgroup.exceptions[0], errors.TooShortHistoryError):
            return subgroup.exceptions[0].minimal_returns_days

        subgroup = subgroup.exceptions[0]


class Ctx(Protocol):
    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def delete(self, entity: domain.Entity) -> None: ...

    async def count_models(self) -> int: ...

    async def next_model_for_update(self) -> evolve.Model: ...

    async def sample_models(self, n: int) -> list[evolve.Model]: ...


class Result(BaseModel):
    day: domain.Day
    alfa: list[FiniteFloat]
    llh: list[FiniteFloat]
    models_count: PositiveInt

    @classmethod
    def from_model(cls, model: evolve.Model, models_count: int) -> Self:
        return cls(
            day=model.day,
            alfa=model.alfa,
            llh=model.llh,
            models_count=models_count,
        )


class EvolutionHandler:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()
        self._builder = builder.Builder()

    async def __call__(
        self,
        ctx: Ctx,
        msg: handler.DataChecked,
    ) -> handler.ModelDeleted | handler.ModelEvaluated:
        count = await self._init_evolution(ctx)
        evolution = await self._init_step(ctx, msg)
        model = await self._get_model(ctx, evolution)
        self._lgr.info(
            "Day %s step %d models %d: %s - %s",
            evolution.day,
            evolution.step,
            count,
            evolution.state,
            model,
        )

        old_result = Result.from_model(model, count)

        try:
            await self._update_model_metrics(ctx, evolution, model)
        except* errors.DomainError as err:
            await self._delete_model_on_error(ctx, evolution, model, err)

            event = handler.ModelDeleted(day=evolution.day, uid=model.uid)
        else:
            return await self._eval_model(ctx, evolution, model, old_result)

        return event

    async def _init_evolution(self, ctx: Ctx) -> int:
        if count := await ctx.count_models():
            return count

        self._lgr.info("Creating start models")
        await ctx.get_for_update(evolve.Model, _random_uid())

        return 1

    async def _init_step(self, ctx: Ctx, msg: handler.DataChecked) -> evolve.Evolution:
        evolution = await ctx.get_for_update(evolve.Evolution)

        match evolution.day == msg.day:
            case True:
                evolution.step += 1
            case False:
                port = await ctx.get(portfolio.Portfolio)
                evolution.init_new_day(
                    msg.day,
                    tuple(pos.ticker for pos in port.positions),
                    port.forecast_days,
                )

        return evolution

    async def _get_model(self, ctx: Ctx, evolution: evolve.Evolution) -> evolve.Model:
        match evolution.state:
            case evolve.State.EVAL_NEW_BASE_MODEL:
                return await ctx.next_model_for_update()
            case evolve.State.EVAL_MODEL:
                model = await ctx.next_model_for_update()
                if model.uid == evolution.base_model_uid:
                    evolution.state = evolve.State.REEVAL_CURRENT_BASE_MODEL

                if model.ver == 0:
                    await ctx.delete(model)
                    self._lgr.info("Untrained model deleted")

                    return await self._get_model(ctx, evolution)

                if model.day < evolution.day:
                    evolution.state = evolve.State.EVAL_OUTDATE_MODEL

                return model
            case evolve.State.EVAL_OUTDATE_MODEL:
                raise errors.UseCasesError(f"can't be in {evolution.state} state")
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                raise errors.UseCasesError(f"can't be in {evolution.state} state")
            case evolve.State.CREATE_NEW_MODEL:
                model = await ctx.get(evolve.Model, evolution.base_model_uid)

                return await self._make_child(ctx, model)

    async def _make_child(self, ctx: Ctx, model: evolve.Model) -> evolve.Model:
        parents = await ctx.sample_models(_PARENT_COUNT)
        if len({parent.uid for parent in parents}) != _PARENT_COUNT:
            parents = [evolve.Model(day=model.day, rev=model.rev) for _ in range(_PARENT_COUNT)]

        child = await ctx.get_for_update(evolve.Model, _random_uid())
        child.genes = model.make_child_genes(parents[0], parents[1], 1 / model.ver)
        child.train_load = model.train_load

        return child

    async def _update_model_metrics(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> None:
        model.day = evolution.day
        model.tickers = evolution.tickers
        model.forecast_days = evolution.forecast_days

        tr = trainer.Trainer(self._builder)
        await tr.update_model_metrics(ctx, model, int(evolution.test_days))

    async def _delete_model_on_error(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
        err: BaseExceptionGroup[errors.DomainError],
    ) -> None:
        await ctx.delete(model)
        self._lgr.info("Model deleted - %s...", err.exceptions[0])

        minimal_returns_days = _extract_minimal_returns_days(err)
        if minimal_returns_days is not None and evolution.state is not evolve.State.CREATE_NEW_MODEL:
            evolution.minimal_returns_days = max(evolution.minimal_returns_days + 1, minimal_returns_days)
            self._lgr.warning("Minimal return days increased - %d", evolution.minimal_returns_days)

        match evolution.state:
            case evolve.State.EVAL_NEW_BASE_MODEL:
                ...
            case evolve.State.EVAL_MODEL:
                ...
            case evolve.State.EVAL_OUTDATE_MODEL:
                evolution.state = evolve.State.EVAL_MODEL
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                evolution.state = evolve.State.EVAL_NEW_BASE_MODEL
            case evolve.State.CREATE_NEW_MODEL:
                evolution.state = evolve.State.EVAL_MODEL

    async def _eval_model(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
        old_result: Result,
    ) -> handler.ModelDeleted | handler.ModelEvaluated:
        match evolution.state:
            case evolve.State.EVAL_NEW_BASE_MODEL:
                evolution.new_base(model)
                evolution.state = evolve.State.EVAL_MODEL
                self._lgr.info(f"New base {model.stats} {model.diff_stats}")
            case evolve.State.EVAL_MODEL:
                if self._should_delete(evolution, model):
                    evolution.state = evolve.State.EVAL_NEW_BASE_MODEL
                    await ctx.delete(model)
                    self._lgr.info(f"{model.stats} {model.diff_stats} deleted - low metrics")

                    return handler.ModelDeleted(day=evolution.day, uid=model.uid)

                evolution.new_base(model)
                self._lgr.info(f"New base {model.stats} {model.diff_stats}")
                evolution.state = evolve.State.CREATE_NEW_MODEL
            case evolve.State.EVAL_OUTDATE_MODEL:
                if self._should_delete(evolution, model):
                    evolution.state = evolve.State.EVAL_NEW_BASE_MODEL
                    await ctx.delete(model)
                    self._lgr.info(f"{model.stats} {model.diff_stats} deleted - low metrics")

                    return handler.ModelDeleted(day=evolution.day, uid=model.uid)

                evolution.new_base(model)
                self._lgr.info(f"New base {model.stats} {model.diff_stats}")
                evolution.state = evolve.State.EVAL_MODEL
            case evolve.State.CREATE_NEW_MODEL:
                if self._should_delete(evolution, model):
                    evolution.state = evolve.State.EVAL_MODEL
                    await ctx.delete(model)
                    self._lgr.info(f"{model.stats} {model.diff_stats} deleted - low metrics")

                    return handler.ModelDeleted(day=evolution.day, uid=model.uid)

                evolution.new_base(model)
                evolution.state = evolve.State.CREATE_NEW_MODEL
                self._lgr.info(f"New base {model.stats} {model.diff_stats}")
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                evolution.new_base(model)
                evolution.state = evolve.State.CREATE_NEW_MODEL
                self._lgr.info(f"Current base {model.stats} {model.diff_stats} reevaluated")

        self._update_test_days(evolution, model)
        self._change_t_critical(evolution, model, old_result)

        base_load = model.duration**0.5 * (1 - abs(model.alfa_diff.p - 0.5) + abs(model.llh_diff.p - 0.5))
        evolution.load_factor = max(evolution.load_factor, 1 / base_load)
        model.train_load += round(base_load * evolution.load_factor)

        return handler.ModelEvaluated(day=evolution.day, uid=model.uid)

    def _update_test_days(self, evolution: evolve.Evolution, model: evolve.Model) -> None:
        old_test_days = int(evolution.test_days)

        match model.alfa_mean < 0:
            case True:
                evolution.test_days += 1
            case False:
                evolution.test_days = max(1, evolution.test_days - consts.P_VALUE / (1 - consts.P_VALUE))

        if old_test_days != (new_test_days := int(evolution.test_days)):
            self._lgr.warning("Test days changed - %d -> %d", old_test_days, new_test_days)

    def _should_delete(
        self,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> bool:
        delete = False

        alfa_delta = _delta(model.alfa, evolution.alfa)
        model.alfa_diff.add(alfa_delta)
        alfa_delta_critical = evolution.alfa_delta_critical
        sign = ">"

        if alfa_delta < alfa_delta_critical:
            delete = True
            sign = "<"

        self._lgr.info(f"Alfa: delta({alfa_delta:.2%}) {sign} delta-critical({alfa_delta_critical:.2%})")

        llh_delta = _delta(model.llh, evolution.llh)
        model.llh_diff.add(llh_delta)
        llh_delta_critical = evolution.llh_delta_critical
        sign = ">"

        if llh_delta < llh_delta_critical:
            delete = True
            sign = "<"

        self._lgr.info(f"LLH: delta({llh_delta:.4f}) {sign} delta-critical({llh_delta_critical:.4f})")

        return delete

    def _change_t_critical(
        self,
        evolution: evolve.Evolution,
        model: evolve.Model,
        old_result: Result,
    ) -> None:
        if model.day != old_result.day:
            return

        alfa_delta = _delta(model.alfa, old_result.alfa)
        old_alfa_delta_critical = evolution.alfa_delta_critical

        sign = ">"

        match alfa_delta < old_alfa_delta_critical:
            case True:
                sign = "<"
                evolution.alfa_delta_critical -= (1 - consts.P_VALUE / 2) * _CRITICAL_FACTOR
            case False:
                evolution.alfa_delta_critical = min(
                    0, evolution.alfa_delta_critical + consts.P_VALUE / 2 * _CRITICAL_FACTOR
                )

        self._lgr.info(
            f"Alfa change: delta({alfa_delta:.2%}) {sign} delta-critical({old_alfa_delta_critical:.2%}) "
            f"-> delta-critical({evolution.alfa_delta_critical:.2%})"
        )

        llh_delta = _delta(model.llh, old_result.llh)
        old_llh_delta_critical = evolution.llh_delta_critical

        sign = ">"

        match llh_delta < old_llh_delta_critical:
            case True:
                sign = "<"
                evolution.llh_delta_critical -= (1 - consts.P_VALUE / 2) * _CRITICAL_FACTOR
            case False:
                evolution.llh_delta_critical = min(
                    0, evolution.llh_delta_critical + consts.P_VALUE / 2 * _CRITICAL_FACTOR
                )

        self._lgr.info(
            f"LLH change: delta({llh_delta:.4f}) {sign} delta-critical({old_llh_delta_critical:.4f}) "
            f"-> delta-critical({evolution.llh_delta_critical:.4f})"
        )


def _delta(target: list[float], base: list[float]) -> float:
    return statistics.mean(map(operator.sub, target, base))
