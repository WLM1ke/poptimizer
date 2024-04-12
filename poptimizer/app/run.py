import asyncio
from collections.abc import Awaitable
from datetime import timedelta
from types import TracebackType
from typing import Final, Protocol

from poptimizer.adapters import uow
from poptimizer.core import domain, errors

_DEFAULT_FIRST_RETRY: Final = timedelta(seconds=30)
_DEFAULT_BACKOFF_FACTOR: Final = 2


class _Action[**P, R](Protocol):
    async def __call__(self, ctx: domain.Ctx, *args: P.args, **kwargs: P.kwargs) -> R: ...


class _SimpleTask[**P, R]:
    def __init__(
        self,
        action: _Action[P, R],
        ctx_factory: uow.CtxFactory,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._action_coro = self._execute(action, ctx_factory, *args, **kwargs)

    async def __call__(self) -> R:
        return await self._action_coro

    async def _execute(
        self,
        action: _Action[P, R],
        ctx_factory: uow.CtxFactory,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        ctx = ctx_factory()
        component_name = domain.get_component_name(action)
        async with ctx:
            result = await action(ctx, *args, **kwargs)
            ctx.info(f"{component_name} finished")

            return result


class _ShieldedTask[**P, R]:
    def __init__(
        self,
        action: _Action[P, R],
        ctx_factory: uow.CtxFactory,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._action_coro = self._execute(action, ctx_factory, *args, **kwargs)

    async def __call__(self) -> R:
        try:
            return await asyncio.shield(self._action_coro)
        except asyncio.CancelledError:
            return await self._action_coro

    async def _execute(
        self,
        action: _Action[P, R],
        ctx_factory: uow.CtxFactory,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        ctx = ctx_factory()
        component_name = domain.get_component_name(action)
        try:
            async with ctx:
                result = await action(ctx, *args, **kwargs)
                ctx.info(f"{component_name} finished")

                return result
        except* errors.POError as err:
            error_msg = f"{", ".join(map(str, err.exceptions))}"
            ctx.warn(f"{component_name} failed - {error_msg}")

            raise asyncio.CancelledError from err


class _RetryTask[**P, R]:
    def __init__(
        self,
        action: _Action[P, R],
        ctx_factory: uow.CtxFactory,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._action_coro = self._execute(action, ctx_factory, *args, **kwargs)
        self._canceled_event = asyncio.Event()

    async def __call__(self) -> R:
        try:
            return await asyncio.shield(self._action_coro)
        except asyncio.CancelledError:
            self._canceled_event.set()
            return await self._action_coro

    async def _execute(
        self,
        action: _Action[P, R],
        ctx_factory: uow.CtxFactory,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        next_retry_time = _DEFAULT_FIRST_RETRY / _DEFAULT_BACKOFF_FACTOR
        component_name = domain.get_component_name(action)

        async with asyncio.TaskGroup() as tg:
            while not self._canceled_event.is_set():
                ctx = ctx_factory()
                try:
                    async with ctx:
                        result = await action(ctx, *args, **kwargs)
                        ctx.info(f"{component_name} finished")

                        return result
                except* errors.POError as err:
                    error_msg = f"{", ".join(map(str, err.exceptions))}"
                    ctx.warn(f"{component_name} failed - {error_msg}")

                next_retry_time *= _DEFAULT_BACKOFF_FACTOR
                ctx.info(f"{component_name} waiting for retry in {next_retry_time}")

                retry_task = tg.create_task(asyncio.sleep(next_retry_time.total_seconds()))
                canceled_task = tg.create_task(self._canceled_event.wait())
                retry_task.add_done_callback(canceled_task.cancel)
                canceled_task.add_done_callback(retry_task.cancel)

                await retry_task

        raise asyncio.CancelledError


class Runner:
    def __init__(self, ctx_factory: uow.CtxFactory) -> None:
        self._tg = asyncio.TaskGroup()
        self._ctx_factory = ctx_factory

    async def __aenter__(self) -> asyncio.TaskGroup:
        return await self._tg.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return await self._tg.__aexit__(exc_type, exc_value, traceback)

    def run[**P, R](
        self,
        action: _Action[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Awaitable[R]:
        return self._tg.create_task(_SimpleTask(action, self._ctx_factory, *args, **kwargs)())

    def run_shielded[**P, R](
        self,
        action: _Action[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Awaitable[R]:
        return self._tg.create_task(_ShieldedTask(action, self._ctx_factory, *args, **kwargs)())

    def run_with_retry[**P, R](
        self,
        action: _Action[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Awaitable[R]:
        return self._tg.create_task(_RetryTask(action, self._ctx_factory, *args, **kwargs)())
