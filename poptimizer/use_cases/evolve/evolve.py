import logging
import operator
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
    def publish(self, msg: handler.Event) -> None: ...
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

    async def next_model_for_update(self, uid: domain.UID) -> tuple[evolve.Model, bool]: ...

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
    ) -> None:
        evolution, count = await self._init_step(ctx, msg)
        model, good = await self._get_model(ctx, evolution)
        self._lgr.info(
            "Day %s step %d models %d: %s - %s",
            evolution.day,
            evolution.step,
            count,
            evolution.state,
            model,
        )

        try:
            await self._update_model_metrics(ctx, evolution, model)
        except* errors.DomainError as err:
            await self._delete_model_on_error(ctx, evolution, model, err)

            ctx.publish(handler.ModelDeleted(day=evolution.day, uid=model.uid))
        else:
            ctx.publish(await self._eval_model(ctx, evolution, model, good=good))

    async def _init_step(self, ctx: Ctx, msg: handler.DataChecked) -> tuple[evolve.Evolution, int]:
        evolution = await ctx.get_for_update(evolve.Evolution)

        if not (count := await ctx.count_models()):
            self._lgr.info("Creating start models")
            uid = _random_uid()
            await ctx.get_for_update(evolve.Model, uid)
            evolution.reset(uid)
            count = 1

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

        return evolution, count

    async def _get_model(self, ctx: Ctx, evolution: evolve.Evolution) -> tuple[evolve.Model, bool]:
        match evolution.state:
            case evolve.State.EVAL_NEW_BASE_MODEL:
                return await ctx.next_model_for_update(evolution.base_model_uid)
            case evolve.State.EVAL_MODEL:
                model, good = await ctx.next_model_for_update(evolution.base_model_uid)
                if model.uid == evolution.base_model_uid:
                    evolution.state = evolve.State.REEVAL_CURRENT_BASE_MODEL

                if model.day < evolution.day:
                    evolution.state = evolve.State.EVAL_OUTDATE_MODEL

                return model, good
            case evolve.State.EVAL_OUTDATE_MODEL:
                raise errors.UseCasesError(f"can't be in {evolution.state} state")
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                return await ctx.get_for_update(evolve.Model, evolution.base_model_uid), True
            case evolve.State.CREATE_NEW_MODEL:
                model = await ctx.get(evolve.Model, evolution.base_model_uid)

                return await self._make_child(ctx, model), True

    async def _make_child(self, ctx: Ctx, model: evolve.Model) -> evolve.Model:
        parents = await ctx.sample_models(_PARENT_COUNT)
        if len({parent.uid for parent in parents}) != _PARENT_COUNT:
            parents = [evolve.Model(day=model.day, rev=model.rev) for _ in range(_PARENT_COUNT)]

        child = await ctx.get_for_update(evolve.Model, _random_uid())
        child.genes = model.make_child_genes(parents[0], parents[1], 1 / model.ver)

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
        self._lgr.info(f"{model}")

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
            evolution.minimal_returns_days = max(
                evolution.minimal_returns_days
                + (minimal_returns_days + evolution.test_days > evolution.minimal_returns_days),
                minimal_returns_days,
            )
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
        *,
        good: bool,
    ) -> handler.ModelDeleted | handler.ModelEvaluated:
        match evolution.state:
            case evolve.State.EVAL_NEW_BASE_MODEL:
                evolution.state = evolve.State.EVAL_MODEL
            case evolve.State.EVAL_MODEL:
                if await self._should_delete(ctx, evolution, model):
                    evolution.state = evolve.State.CREATE_NEW_MODEL

                    return handler.ModelDeleted(day=evolution.day, uid=model.uid)

                if good:
                    evolution.state = evolve.State.CREATE_NEW_MODEL
            case evolve.State.EVAL_OUTDATE_MODEL:
                if await self._should_delete(ctx, evolution, model):
                    evolution.state = evolve.State.CREATE_NEW_MODEL

                    return handler.ModelDeleted(day=evolution.day, uid=model.uid)

                evolution.state = evolve.State.EVAL_MODEL
            case evolve.State.CREATE_NEW_MODEL:
                if await self._should_delete(ctx, evolution, model):
                    evolution.state = evolve.State.REEVAL_CURRENT_BASE_MODEL

                    return handler.ModelDeleted(day=evolution.day, uid=model.uid)

                evolution.state = evolve.State.EVAL_MODEL
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                evolution.state = evolve.State.EVAL_MODEL

        evolution.new_base(model)
        self._update_test_days(evolution, model)

        return handler.ModelEvaluated(day=evolution.day, uid=model.uid)

    def _update_test_days(self, evolution: evolve.Evolution, model: evolve.Model) -> None:
        old_test_days = int(evolution.test_days)

        match model.alfa_mean < 0:
            case True:
                evolution.test_days += 1
            case False if model.ret < 0:
                evolution.test_days += 1
            case False:
                evolution.test_days = max(1, evolution.test_days - consts.P_VALUE / (1 - consts.P_VALUE))

        if old_test_days != (new_test_days := int(evolution.test_days)):
            self._lgr.info("Test days changed - %d -> %d", old_test_days, new_test_days)

    async def _should_delete(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> bool:
        old_alfa_p = model.alfa_diff.p
        model.alfa_diff.add(_delta(model.alfa, evolution.alfa))
        self._lgr.info(f"Alfa quality: {old_alfa_p:.2%} -> {model.alfa_diff.p:.2%}")

        old_llh_p = model.llh_diff.p
        model.llh_diff.add(_delta(model.llh, evolution.llh))
        self._lgr.info(f"LLH quality: {old_llh_p:.2%} -> {model.llh_diff.p:.2%}")

        if model.alfa_diff.p < consts.P_VALUE / 2:
            self._lgr.info("Deleted - very low alfa quality")
            await ctx.delete(model)

            return True

        if model.llh_diff.p < consts.P_VALUE / 2:
            self._lgr.info("Deleted - very low llh quality")
            await ctx.delete(model)

            return True

        return False


def _delta(target: list[float], base: list[float]) -> list[float]:
    return list(map(operator.sub, target, base))
