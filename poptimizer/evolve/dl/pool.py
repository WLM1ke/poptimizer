import asyncio
import contextlib
import multiprocessing as mp
import signal
from collections.abc import Callable
from concurrent.futures import Future, InvalidStateError
from types import TracebackType
from typing import Self


def _finish[R](future: Future[R], result: R) -> None:
    with contextlib.suppress(InvalidStateError):
        future.set_result(result)


def _fail[R](future: Future[R], err: BaseException) -> None:
    with contextlib.suppress(InvalidStateError):
        future.set_exception(err)


def _ignore_sigint() -> None:
    # Ctrl-C reaches every process in the terminal's group; the worker must survive it and let
    # the parent terminate the pool on shutdown, otherwise multiprocessing prints its traceback.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


class PoolTrainingRunner[J, D, R]:
    def __init__(self, worker: Callable[[J, D], R]) -> None:
        self._worker = worker
        self._pool = mp.get_context("spawn").Pool(
            processes=1,
            maxtasksperchild=1,
            initializer=_ignore_sigint,
        )

    async def __call__(self, job: J, data: D) -> R:
        future = Future[R]()
        self._pool.apply_async(
            self._worker,
            (job, data),
            callback=lambda result: _finish(future, result),
            error_callback=lambda err: _fail(future, err),
        )

        return await asyncio.wrap_future(future)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self._pool.terminate()
        self._pool.join()
