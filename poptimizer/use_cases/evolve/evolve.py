import logging
import operator
import statistics
from typing import Final, Protocol

import bson

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler, view
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
    def __init__(self, viewer: view.Viewer) -> None:
        self._lgr = logging.getLogger()
        self._viewer = viewer

    async def __call__(
        self,
        ctx: Ctx,
        msg: handler.DataNotChanged | handler.DataUpdated,
    ) -> handler.ModelDeleted | handler.ModelEvaluated:
        await self._init_evolution(ctx)
        evolution = await self._init_step(ctx, msg.day)
        model = await self._get_model(ctx, evolution)
        self._lgr.info("Day %s step %d: %s - %s", evolution.day, evolution.step, evolution.state, model)

        try:
            await self._update_model_metrics(model, evolution.day, evolution.tickers, evolution.test_days)
        except* errors.DomainError as err:
            await self._delete_model(ctx, evolution, model, err)

            event = handler.ModelDeleted(day=msg.day, uid=model.uid)
        else:
            return await self._eval_model(ctx, evolution, model)

        return event

    async def _init_evolution(self, ctx: Ctx) -> None:
        if not await ctx.count_models():
            self._lgr.info("Creating initial models")
            for _ in range(consts.INITIAL_POPULATION):
                model = await ctx.get_for_update(evolve.Model, _random_uid())
                model.alfas = [0]

    async def _init_step(self, ctx: Ctx, day: domain.Day) -> evolve.Evolution:
        evolution = await ctx.get_for_update(evolve.Evolution)

        match evolution.day == day:
            case True:
                evolution.step += 1
            case False:
                port = await ctx.get(portfolio.Portfolio)
                evolution.init_new_day(day, port.tickers())

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
        model: evolve.Model,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
        test_days: int,
    ) -> None:
        tr = trainer.Trainer(builder.Builder(self._viewer))
        await tr.update_model_metrics(model, day, tickers, test_days)

    async def _delete_model(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        model: evolve.Model,
        err: BaseExceptionGroup[errors.DomainError],
    ) -> None:
        await ctx.delete(model)
        self._lgr.warning("Model deleted - %s...", err.exceptions[0])

        minimal_returns_days = _extract_minimal_returns_days(err)
        if minimal_returns_days is not None and evolution.state is not evolve.State.CREATE_NEW_MODEL:
            if evolution.more_tests:
                evolution.more_tests = False
                self._lgr.warning("Stop increasing test days for today - %d", evolution.test_days)

            if minimal_returns_days > evolution.minimal_returns_days:
                evolution.minimal_returns_days += 1
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
                self._lgr.info(f"New base Model(alfa={model.alfa:.2%})")
            case evolve.State.EVAL_MODEL:
                if self._should_delete(evolution, model):
                    evolution.state = evolve.State.EVAL_MODEL
                    await ctx.delete(model)
                    self._lgr.info(f"Model(alfa={model.alfa:.2%}) deleted - low metrics")

                    return handler.ModelDeleted(day=model.day, uid=model.uid)

                evolution.new_base(model)
                self._lgr.info(f"New base Model(alfa={model.alfa:.2%}) set")
                evolution.state = evolve.State.CREATE_NEW_MODEL
            case evolve.State.CREATE_NEW_MODEL:
                if self._should_delete(evolution, model):
                    evolution.state = evolve.State.EVAL_MODEL
                    await ctx.delete(model)
                    self._lgr.info(f"Model(alfa={model.alfa:.2%}) deleted - low metrics")

                    return handler.ModelDeleted(day=model.day, uid=model.uid)

                evolution.new_base(model)
                evolution.state = evolve.State.CREATE_NEW_MODEL
                self._lgr.info(f"New base Model(alfa={model.alfa:.2%}) set")

                if await ctx.count_models() > evolution.test_days:
                    evolution.delta_critical = 0
                    if evolution.more_tests:
                        evolution.test_days += 1
                        self._lgr.warning("Test days increased - %d", evolution.test_days)
            case evolve.State.REEVAL_CURRENT_BASE_MODEL:
                self._change_t_critical(evolution, model)
                evolution.new_base(model)
                evolution.state = evolve.State.CREATE_NEW_MODEL
                self._lgr.info(f"Current base Model(alfa={model.alfa:.2%}) reevaluated")

        return handler.ModelEvaluated(day=model.day, uid=model.uid)

    def _should_delete(
        self,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> bool:
        delta = _delta(model.alfas, evolution.alfas)
        adj_delta_critical = evolution.adj_delta_critical(model.duration)

        sign = ">"
        delete = False

        if delta < adj_delta_critical:
            delete = True
            if delta < adj_delta_critical:
                sign = "<"
        self._lgr.info(
            f"Delta({delta:.2%}) {sign} adj-delta-critical({adj_delta_critical:.2%}), "
            f"delta-critical({evolution.delta_critical:.2%})",
        )

        return delete

    def _change_t_critical(
        self,
        evolution: evolve.Evolution,
        model: evolve.Model,
    ) -> None:
        delta = _delta(model.alfas, evolution.alfas)
        adj_delta_critical = evolution.adj_delta_critical(model.duration)
        old_delta_critical = evolution.delta_critical

        sign_alfa = ">"

        match delta < adj_delta_critical:
            case True:
                if delta < adj_delta_critical:
                    sign_alfa = "<"
                evolution.delta_critical -= (1 - consts.P_VALUE) / evolution.test_days
            case False:
                evolution.delta_critical = min(0, evolution.delta_critical + consts.P_VALUE / evolution.test_days)

        self._lgr.info(
            f"Delta({delta:.2%}) {sign_alfa} adj-delta-critical({adj_delta_critical:.2%}), "
            f"changing delta-critical({old_delta_critical:.2%}) -> delta-critical({evolution.delta_critical:.2%})"
        )


def _delta(target: list[float], base: list[float]) -> float:
    return statistics.mean(map(operator.sub, target, base))
