import asyncio
import multiprocessing as mp
import signal
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from types import TracebackType
from typing import Self


def _ignore_sigint() -> None:
    # Ctrl-C reaches every process in the terminal's group; the worker must survive it and let
    # the parent terminate the pool on shutdown, otherwise multiprocessing prints its traceback.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


class PoolTrainingRunner[J, D, R]:
    def __init__(self, worker: Callable[[J, D], R]) -> None:
        self._worker = worker
        self._executor = ProcessPoolExecutor(
            max_workers=1,
            mp_context=mp.get_context("spawn"),
            initializer=_ignore_sigint,
            max_tasks_per_child=1,
        )

    async def __call__(self, job: J, data: D) -> R:
        return await asyncio.wrap_future(self._executor.submit(self._worker, job, data))

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self._executor.terminate_workers()
        self._executor.shutdown(wait=True)
