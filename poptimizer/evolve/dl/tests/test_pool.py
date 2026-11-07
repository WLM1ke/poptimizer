import asyncio
import os
import signal
import time

import pytest

from poptimizer.core import errors
from poptimizer.evolve.dl import pool


def _double_worker(num: int, _: int) -> int:
    return num * 2


def _raise_too_short_history(num: int, _: int) -> int:
    raise errors.TooShortHistoryError("TEST", num)


def _sleep_worker(seconds: int, _: int) -> int:
    time.sleep(seconds)

    return seconds


def _signal_handler_worker(_: int, __: int) -> bool:
    return signal.getsignal(signal.SIGINT) is signal.SIG_IGN


def _self_sigint_worker(_: int, __: int) -> str:
    os.kill(os.getpid(), signal.SIGINT)
    time.sleep(0.1)

    return "alive"


async def test_result_round_trip():
    async with pool.PoolTrainingRunner(_double_worker) as runner:
        assert await runner(21, 0) == 42


async def test_exception_pickle_round_trip():
    async with pool.PoolTrainingRunner(_raise_too_short_history) as runner:
        with pytest.raises(errors.TooShortHistoryError) as exc_info:
            await runner(42, 0)

        assert exc_info.value.minimal_returns_days == 42


async def test_exit_terminates_in_flight_run():
    async with pool.PoolTrainingRunner(_sleep_worker) as runner:
        run_task = asyncio.create_task(runner(60, 0))
        await asyncio.sleep(1)

    assert not run_task.done()
    with pytest.raises(ValueError, match="Pool not running"):
        await runner(1, 0)

    run_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task


async def test_cancellation_propagates_promptly():
    async with pool.PoolTrainingRunner(_sleep_worker) as runner:
        run_task = asyncio.create_task(runner(60, 0))
        await asyncio.sleep(1)

        run_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(run_task, timeout=5)


async def test_cancelled_future_does_not_break_result_handler():
    async with pool.PoolTrainingRunner(_sleep_worker) as runner:
        run_task = asyncio.create_task(runner(1, 0))
        await asyncio.sleep(0.2)

        run_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await run_task
        await asyncio.sleep(1.5)  # the worker finishes and its callback hits the cancelled future

        assert await asyncio.wait_for(runner(0, 0), timeout=10) == 0


async def test_worker_starts_with_ignored_sigint():
    async with pool.PoolTrainingRunner(_signal_handler_worker) as runner:
        assert await asyncio.wait_for(runner(0, 0), timeout=30) is True


async def test_worker_survives_sigint():
    async with pool.PoolTrainingRunner(_self_sigint_worker) as runner:
        assert await asyncio.wait_for(runner(0, 0), timeout=30) == "alive"


async def test_context_manager_closes_pool():
    async with pool.PoolTrainingRunner(_double_worker) as runner:
        assert await runner(21, 0) == 42

    with pytest.raises(ValueError, match="Pool not running"):
        await runner(1, 0)


async def test_context_manager_closes_pool_after_error():
    with pytest.raises(RuntimeError, match="boom"):
        async with pool.PoolTrainingRunner(_double_worker) as runner:
            raise RuntimeError("boom")

    with pytest.raises(ValueError, match="Pool not running"):
        await runner(1, 0)
