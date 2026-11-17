import asyncio
import logging
import random
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Final, Protocol

from poptimizer.core import errors

_FIRST_DELAY: Final = 30.0
_BACKOFF_FACTOR: Final = 4.0


class Step[R, **P, T](Protocol):
    async def __call__(self, repo: R, *args: P.args, **kwargs: P.kwargs) -> T: ...


def _step_name(step: object) -> str:
    name = getattr(step, "__name__", None)

    return name if isinstance(name, str) else step.__class__.__name__


class Retrier[R]:
    def __init__(
        self,
        uow_factory: Callable[[], AbstractAsyncContextManager[R]],
        *,
        first_delay: float = _FIRST_DELAY,
        factor: float = _BACKOFF_FACTOR,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._lgr = logging.getLogger(self.__class__.__name__)
        self._uow_factory = uow_factory
        self._first_delay = first_delay
        self._factor = factor
        self._jitter = jitter

    async def __call__[**P, T](self, step: Step[R, P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        delay = self._first_delay

        while True:
            try:
                async with self._uow_factory() as repo:
                    return await step(repo, *args, **kwargs)
            except* errors.POError as err:
                failure = errors.get_root_poptimizer_error(err)

            self._lgr.warning(f"Retrying {_step_name(step)} in {delay} sec - {failure}")

            await asyncio.sleep(delay)
            delay = self._next_delay(delay)

    def _next_delay(self, delay: float) -> float:
        return delay * self._factor * self._jitter()
