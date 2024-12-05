import logging
import time
from typing import Final, Protocol

import bson

from poptimizer import errors
from poptimizer.domain import domain
from poptimizer.domain.dl import training
from poptimizer.domain.evolve import evolve, model
from poptimizer.use_cases import handler, view
from poptimizer.use_cases.dl import builder, trainer

_PARENT_COUNT: Final = 2


def random_org_uid() -> domain.UID:
    return domain.UID(str(bson.ObjectId()))


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

    async def count_orgs(self) -> int: ...

    async def next_org_for_update(self) -> model.Model: ...

    async def sample_orgs(self, n: int) -> list[model.Model]: ...


class EvolutionHandler:
    def __init__(self, viewer: view.Viewer) -> None:
        self._lgr = logging.getLogger()
        self._viewer = viewer

    async def __call__(
        self,
        ctx: Ctx,
        msg: handler.DataNotChanged | handler.DataUpdated,
    ) -> handler.EvolutionStepFinished | tuple[handler.EvolutionStepFinished, handler.ForecastCreated]:
        evolution = await ctx.get_for_update(evolve.Evolution)
        state = evolution.start_step(msg.day)
        self._lgr.info("%s", evolution)

        match state:
            case evolve.State.INIT:
                org = await ctx.get_for_update(model.Model, random_org_uid())
                await self._init_day(ctx, evolution, org)
            case evolve.State.INIT_DAY:
                org = await self._next_org(ctx)
                await self._init_day(ctx, evolution, org)
            case evolve.State.NEW_BASE_ORG:
                org = await self._next_org(ctx)
                await self._new_base_org(ctx, evolution, org)
            case evolve.State.EVAL_ORG:
                org = await self._next_org(ctx)
                await self._eval_org(ctx, evolution, org)
            case evolve.State.CREATE_ORG:
                org = await ctx.get(model.Model, evolution.org_uid)
                org = await self._make_child(ctx, org)
                await self._eval_org(ctx, evolution, org)

        return (handler.EvolutionStepFinished(day=msg.day), handler.ForecastCreated(day=msg.day))

    async def _init_day(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        org: model.Model,
    ) -> None:
        tickers = await self._viewer.portfolio_tickers()

        try:
            duration, training_result = await self._eval(ctx, org, evolution.day, tickers)
        except* errors.DomainError as err:
            await self._delete_org(ctx, evolution, org, err)
        else:
            evolution.init_new_day(tickers, org.uid, training_result.alfas, training_result.llh, duration)

    async def _new_base_org(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        org: model.Model,
    ) -> None:
        try:
            duration, training_result = await self._eval(ctx, org, evolution.day, evolution.tickers)
        except* errors.DomainError as err:
            await self._delete_org(ctx, evolution, org, err)
        else:
            evolution.new_base_org(org.uid, training_result.alfas, training_result.llh, duration)

    async def _eval_org(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        org: model.Model,
    ) -> None:
        try:
            duration, training_result = await self._eval(ctx, org, evolution.day, evolution.tickers)
        except* errors.DomainError as err:
            await self._delete_org(ctx, evolution, org, err)
        else:
            dead, msg1, msg2 = evolution.eval_org_is_dead(org.uid, training_result.alfas, training_result.llh, duration)
            self._lgr.info(msg1)
            self._lgr.info(msg2)

            if dead:
                await ctx.delete(org)
                self._lgr.info("Organism removed")

    async def _next_org(self, ctx: Ctx) -> model.Model:
        org = await ctx.next_org_for_update()
        while not org.ver:
            await ctx.delete(org)
            org = await ctx.next_org_for_update()

        return org

    async def _delete_org(
        self,
        ctx: Ctx,
        evolution: evolve.Evolution,
        org: model.Model,
        err: BaseExceptionGroup[errors.DomainError],
    ) -> None:
        await ctx.delete(org)

        self._lgr.warning("Delete %s - %s, ...", org, err.exceptions[0])

        if (return_days := evolution.org_failed(org.uid, err)) is not None:
            self._lgr.warning("Minimal return days increased - %d", return_days)

    async def _make_child(self, ctx: Ctx, org: model.Model) -> model.Model:
        parents = await ctx.sample_orgs(_PARENT_COUNT)
        if len({parent.uid for parent in parents}) != _PARENT_COUNT:
            parents = [model.Model(day=org.day, rev=org.rev) for _ in range(_PARENT_COUNT)]

        child = await ctx.get_for_update(model.Model, random_org_uid())
        child.genes = org.make_child_genes(parents[0], parents[1], 1 / org.ver)

        return child

    async def _eval(
        self,
        ctx: Ctx,
        org: model.Model,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
    ) -> tuple[
        float,
        training.Result,
    ]:
        start = time.monotonic()
        cfg = trainer.Cfg.model_validate(org.phenotype)
        test_days = 1 + await ctx.count_orgs()

        tr = trainer.Trainer(builder.Builder(self._viewer))
        training_result = await tr.run(day, tickers, test_days, cfg)

        org.update_stats(day, tickers, training_result)

        self._lgr.info("%s", org)

        return time.monotonic() - start, training_result
