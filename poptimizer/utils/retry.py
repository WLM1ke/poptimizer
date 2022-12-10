"""Декоратор для экспоненциального повторного вызова."""
import asyncio
import logging
from functools import wraps
from typing import Awaitable, Callable, ParamSpec, TypeVar

from pydantic import BaseModel, Field

_FuncParams = ParamSpec("_FuncParams")
_FuncReturn = TypeVar("_FuncReturn")


class Policy(BaseModel):
    """Политика осуществления повторов."""

    attempts: int = Field(ge=2)
    start_timeout_sec: float = Field(gt=0)
    factor: float = Field(ge=1)
    exceptions: type[BaseException] | tuple[type[BaseException]]


class AsyncExponential:
    """Декоратор для экспоненциального повторного вызова асинхронных функций."""

    def __init__(
        self,
        policy: Policy,
        logger: logging.Logger,
    ) -> None:
        self._attempts = policy.attempts
        self._start_timeout_sec = policy.start_timeout_sec
        self._factor = policy.factor
        self._exceptions = policy.exceptions
        self._logger = logger

    def __call__(
        self,
        func: Callable[_FuncParams, Awaitable[_FuncReturn]],
    ) -> Callable[_FuncParams, Awaitable[_FuncReturn]]:
        """Декоратор, осуществляющий повторный вызов в случае исключений."""

        @wraps(func)
        async def _wrap(  # noqa: WPS430
            *args: _FuncParams.args,
            **kwargs: _FuncParams.kwargs,
        ) -> _FuncReturn:
            timeout = self._start_timeout_sec
            count = 1

            while True:
                try:
                    return await func(*args, **kwargs)
                except self._exceptions as err:
                    self._logger.debug(f"attempt %d -> %s", count, err)

                    last_exc = err

                if count == self._attempts:
                    raise last_exc

                await asyncio.sleep(timeout)

                timeout *= self._factor
                count += 1

        return _wrap
