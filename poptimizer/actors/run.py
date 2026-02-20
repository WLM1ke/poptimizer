import asyncio
import logging
import random
import traceback as tb
from datetime import timedelta
from types import TracebackType
from typing import Final, Protocol

from poptimizer.core import actors, errors

_FIRST_RETRY: Final = timedelta(seconds=30)
_BACKOFF_FACTOR: Final = 2


class _Tx[C](Protocol):
    async def __aenter__(self) -> C: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


async def with_retry[C, **I, O](
    lrg: logging.Logger,
    handler: actors.Handler[C, I, O],
    tx: _Tx[C],
    *args: I.args,
    **kwargs: I.kwargs,
) -> O:
    last_delay = _FIRST_RETRY / _BACKOFF_FACTOR

    while True:
        match await _run_safe(handler, tx, *args, **kwargs):
            case errors.POError() as err:
                last_delay = await _next_delay(last_delay)
                lrg.warning(
                    "failed with %s - retrying in %s",
                    err,
                    last_delay,
                )

                await asyncio.sleep(last_delay.total_seconds())
            case _ as output:
                return output


async def run_safe[C, **I](
    lrg: logging.Logger,
    handler: actors.Handler[C, I, None],
    tx: _Tx[C],
    *args: I.args,
    **kwargs: I.kwargs,
) -> None:
    if (err := await _run_safe(handler, tx, *args, **kwargs)) is not None:
        lrg.warning("failed with %s", err)


async def _run_safe[C, **I, O](
    handler: actors.Handler[C, I, O],
    tx: _Tx[C],
    *args: I.args,
    **kwargs: I.kwargs,
) -> O | errors.POError:
    err_out: errors.POError = errors.POError()

    try:
        async with tx as ctx:
            return await handler(ctx, *args, **kwargs)
    except* errors.POError as err:
        tb.print_exception(err, colorize=True)  # type: ignore[reportCallIssue]

        err_out = errors.get_root_poptimizer_error(err)

    return err_out


async def _next_delay(delay: timedelta) -> timedelta:
    return timedelta(seconds=delay.total_seconds() * _BACKOFF_FACTOR * 2 * random.random())  # noqa: S311
