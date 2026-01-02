import asyncio
import logging
import random
import traceback as tb
from collections.abc import Awaitable, Callable
from datetime import timedelta
from types import TracebackType
from typing import Final, Protocol, Self

from poptimizer import errors
from poptimizer.adapters import adapter

_FIRST_RETRY: Final = timedelta(seconds=30)
_BACKOFF_FACTOR: Final = 2


class UOW[C](Protocol):
    async def __aenter__(self) -> C: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class Handler[C, **I, O](Protocol):
    async def __call__(self, ctx: C, *args: I.args, **kwargs: I.kwargs) -> O: ...


class ContextRunner[C]:
    def __init__(self, uow_provider: Callable[[], UOW[C]]) -> None:
        self._lgr = logging.getLogger()
        self._uow_provider = uow_provider
        self._tg = asyncio.TaskGroup()

    async def __aenter__(self) -> Self:
        await self._tg.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return await self._tg.__aexit__(exc_type, exc_value, traceback)

    def run_with_retry[**I, O](
        self,
        handler: Handler[C, I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> Awaitable[O]:
        return self._tg.create_task(self._run_with_retry(handler, *args, **kwargs))

    async def _run_with_retry[**I, O](
        self,
        handler: Handler[C, I, O],
        *args: I.args,
        **kwargs: I.kwargs,
    ) -> O:
        last_delay = _FIRST_RETRY / _BACKOFF_FACTOR

        while True:
            try:
                async with self._uow_provider() as uow:
                    output = await handler(uow, *args, **kwargs)
            except* errors.POError as err:
                tb.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]

                last_delay = await _next_delay(last_delay)
                self._lgr.warning(
                    "%s failed - retrying in %s",
                    adapter.get_component_name(handler),
                    last_delay,
                )
                await asyncio.sleep(last_delay.total_seconds())
            else:
                self._lgr.info(
                    "%s finished",
                    adapter.get_component_name(handler),
                )

                return output


async def _next_delay(delay: timedelta) -> timedelta:
    seconds = delay.total_seconds()

    return timedelta(seconds=seconds * _BACKOFF_FACTOR * 2 * random.random())  # noqa: S311
