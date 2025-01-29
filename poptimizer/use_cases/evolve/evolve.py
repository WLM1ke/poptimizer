import logging
import operator
import statistics
from typing import Final, Protocol

import bson

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


class EvolutionHandler:
    def __init__(self) -> None:
        self._lgr = logging.getLogger()
        self._builder = builder.Builder()

    async def __call__(
        self,
        ctx: Ctx,
        msg: handler.DataChecked,
    ) -> handler.ModelDeleted | handler.ModelEvaluated:
        await self._init_evolution(ctx)
        evolution = await self._init_step(ctx, msg)
        model = await self._get_model(ctx, evolution)
        self._lgr.info("Day %s step %d: %s - %s", evolution.day, evolution.step, evolution.state, model)

        try:
            await self._update_model_metrics(ctx, evolution, model)
        except* errors.DomainError as err:
            await self._delete_model_on_error(ctx, evolution, model, err)

            event = handler.ModelDeleted(day=evolution.day, portfolio_ver=evolution.portfolio_ver, uid=model.uid)
        else:
            return await self._eval_model(ctx, evolution, model)

        return event

    async def _init_evolution(self, ctx: Ctx) -> None:
        if not await ctx.count_models():
            self._lgr.info("Creating initial models")
            for _ in range(consts.INITIAL_POPULATION):
                await ctx.get_for_update(evolve.Model, _random_uid())

    async def _init_step(self, ctx: Ctx, msg: handler.DataChecked) -> evolve.Evolution:
        evolution = await ctx.get_for_update(evolve.Evolution)

        match evolution.day == msg.day:
            case True:
                evolution.step += 1
            case False:
                evolution.init_new_day(msg.day)

        if evolution.portfolio_ver < msg.portfolio_ver:
            port = await ctx.get(portfolio.Portfolio)
            tickers = tuple(pos.ticker for pos in port.positions)
            evolution.update_portfolio_ver(port.ver, tickers, port.forecast_days)

        return evolution

    async def _get_model(self, ctx: Ctx, evolution: evolve.Evolution) -> evolve.Model:
        match evolution.state:
            case evolve.State.EVAL_NEW_BASE_MODEL:
                return await ctx.next_model_for_update()
            case evolve.State.EVAL_MODEL:
                model = await ctx.next_model_for_update()
                if model.uid == evolution.base_model_uid:
                    evolution.state = evolve.State.REEVAL_CURRENT_BASE_MODEL

                return model
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                raise errors.UseCasesError(f"can't be in {evolve.State.REEVAL_CURRENT_BASE_MODEL} state")
            case evolve.State.CREATE_NEW_MODEL:
                model = await ctx.get(evolve.Model, evolution.base_model_uid)

                return await self._make_child(ctx, model)

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
        await tr.update_model_metrics(ctx, model, evolution.test_days)

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
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                evolution.state = evolve.State.EVAL_NEW_BASE_MODEL
            case evolve.State.CREATE_NEW_MODEL:
                evolution.state = evolve.State.EVAL_MODEL

    async def _eval_model(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> handler.ModelDeleted | handler.ModelEvaluated:
        match evolution.state:
            case evolve.State.EVAL_NEW_BASE_MODEL:
                evolution.new_base(model)
                evolution.state = evolve.State.CREATE_NEW_MODEL
                self._lgr.info(f"New base {model.stats}")
            case evolve.State.EVAL_MODEL:
                if self._should_delete(evolution, model):
                    evolution.state = evolve.State.EVAL_MODEL
                    await ctx.delete(model)
                    self._lgr.info(f"{model.stats} deleted - low metrics")

                    return handler.ModelDeleted(day=evolution.day, portfolio_ver=evolution.portfolio_ver, uid=model.uid)

                evolution.new_base(model)
                self._lgr.info(f"New base {model.stats}")
                evolution.state = evolve.State.CREATE_NEW_MODEL
            case evolve.State.CREATE_NEW_MODEL:
                if self._should_delete(evolution, model):
                    evolution.state = evolve.State.EVAL_MODEL
                    await ctx.delete(model)
                    self._lgr.info(f"{model.stats} deleted - low metrics")

                    return handler.ModelDeleted(day=evolution.day, portfolio_ver=evolution.portfolio_ver, uid=model.uid)

                evolution.new_base(model)
                evolution.state = evolve.State.CREATE_NEW_MODEL
                self._lgr.info(f"New base {model.stats}")

                if model.alfa_mean < 0:
                    evolution.alfa_delta_critical *= 1 - 1 / evolution.test_days
                    evolution.llh_delta_critical *= 1 - 1 / evolution.test_days
                    evolution.test_days += 1
                    self._lgr.warning("Test days increased - %d", evolution.test_days)
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                self._change_t_critical(evolution, model)
                evolution.new_base(model)
                evolution.state = evolve.State.CREATE_NEW_MODEL
                self._lgr.info(f"Current base {model.stats} reevaluated")

        return handler.ModelEvaluated(day=evolution.day, portfolio_ver=evolution.portfolio_ver, uid=model.uid)

    def _should_delete(
        self,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> bool:
        delete = False

        alfa_delta = _delta(model.alfa, evolution.alfa)
        adj_alfa_delta_critical = evolution.adj_alfa_delta_critical(model.duration)
        sign = ">"

        if alfa_delta < adj_alfa_delta_critical:
            delete = True
            sign = "<"

        self._lgr.info(
            f"Alfa: delta({alfa_delta:.2%}) {sign} adj-delta-critical({adj_alfa_delta_critical:.2%}), "
            f"delta-critical({evolution.alfa_delta_critical:.2%})",
        )

        llh_delta = _delta(model.llh, evolution.llh)
        adj_llh_delta_critical = evolution.adj_llh_delta_critical(model.duration)
        sign = ">"

        if llh_delta < adj_llh_delta_critical:
            delete = True
            sign = "<"

        self._lgr.info(
            f"LLH: delta({llh_delta:.4f}) {sign} adj-delta-critical({adj_llh_delta_critical:.4f}), "
            f"delta-critical({evolution.llh_delta_critical:.4f})",
        )

        return delete

    def _change_t_critical(
        self,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> None:
        alfa_delta = _delta(model.alfa, evolution.alfa)
        adj_alfa_delta_critical = evolution.adj_alfa_delta_critical(model.duration)
        old_alfa_delta_critical = evolution.alfa_delta_critical

        sign = ">"

        match alfa_delta < adj_alfa_delta_critical:
            case True:
                sign = "<"
                evolution.alfa_delta_critical -= (1 - consts.P_VALUE / 2) / evolution.test_days
            case False:
                evolution.alfa_delta_critical = min(
                    0, evolution.alfa_delta_critical + consts.P_VALUE / 2 / evolution.test_days
                )

        self._lgr.info(
            f"Alfa: delta({alfa_delta:.2%}) {sign} adj-delta-critical({adj_alfa_delta_critical:.2%}), "
            f"changing delta-critical({old_alfa_delta_critical:.2%}) "
            f"-> delta-critical({evolution.alfa_delta_critical:.2%})"
        )

        llh_delta = _delta(model.llh, evolution.llh)
        adj_llh_delta_critical = evolution.adj_llh_delta_critical(model.duration)
        old_llh_delta_critical = evolution.llh_delta_critical

        sign = ">"

        match llh_delta < adj_llh_delta_critical:
            case True:
                sign = "<"
                evolution.llh_delta_critical -= (1 - consts.P_VALUE / 2) / evolution.test_days
            case False:
                evolution.llh_delta_critical = min(
                    0, evolution.llh_delta_critical + consts.P_VALUE / 2 / evolution.test_days
                )

        self._lgr.info(
            f"LLH: delta({llh_delta:.4f}) {sign} adj-delta-critical({adj_llh_delta_critical:.4f}), "
            f"changing delta-critical({old_llh_delta_critical:.4f}) "
            f"-> delta-critical({evolution.llh_delta_critical:.4f})"
        )


def _delta(target: list[float], base: list[float]) -> float:
    return statistics.mean(map(operator.sub, target, base))
