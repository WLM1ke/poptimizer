import asyncio
import contextlib
import logging
import multiprocessing as mp
import signal
import sys
import warnings
from collections.abc import Callable
from datetime import timedelta
from types import FrameType
from typing import Any, Final

import psutil
import torch
import uvloop

from poptimizer import config
from poptimizer.adapters import http_session, logger, mongo
from poptimizer.cli import safe
from poptimizer.controllers.bus import bus
from poptimizer.controllers.server import server

_MEMORY_PERCENTAGE_THRESHOLD: Final = 100
_CHECK_PERIOD: Final = timedelta(hours=1)


class _SignalHandler:
    def __init__(self, task: asyncio.Task[Any]) -> None:
        self._task = task

    def __call__(self, sig: int, frame: FrameType | None) -> None:  # noqa: ARG002
        self._task.cancel()


async def _run(*, check_memory: bool = False) -> int:
    if check_memory and (main_task := asyncio.current_task()):
        signal.signal(signal.SIGTERM, _SignalHandler(main_task))

    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        stack.enter_context(warnings.catch_warnings())
        warnings.simplefilter("ignore", category=RuntimeWarning)

        http_client = await stack.enter_async_context(http_session.client())
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))

        lgr = await stack.enter_async_context(
            logger.init(
                http_client,
                cfg.telegram_token,
                cfg.telegram_chat_id,
            )
        )

        msg_bus = bus.build(http_client, mongo_db)
        http_server = server.build(msg_bus, cfg.server_url)

        coro = [msg_bus.run(), http_server.run()]
        if check_memory:
            timeout = await stack.enter_async_context(asyncio.Timeout(None))
            coro.append(_memory_checker(lgr, timeout.reschedule))

        return await safe.run(lgr, *coro)

    return 1


async def _memory_checker(lgr: logging.Logger, stop_fn: Callable[[float], None]) -> None:
    proc = psutil.Process()

    while (usage := proc.memory_percent()) < _MEMORY_PERCENTAGE_THRESHOLD:
        lgr.info("Memory usage - %.2f%%", usage)

        await asyncio.sleep(_CHECK_PERIOD.total_seconds())

    lgr.warning("Stopping due to high memory usage - %.2f%%", usage)
    stop_fn(asyncio.get_running_loop().time())


def _run_in_uvloop() -> int:
    with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
        try:
            return runner.run(_run(check_memory=True))
        except asyncio.CancelledError:
            return 0


def _run_in_process() -> int:
    stopping = False

    while True:
        process = mp.Process(target=_run_in_uvloop, daemon=True)
        process.start()

        try:
            process.join()
        except KeyboardInterrupt:
            if process.pid:
                stopping = True
                process.terminate()
                process.join()

        exitcode = process.exitcode
        process.close()

        match exitcode:
            case 0 if stopping:
                return 0
            case 0:
                continue
            case _:
                return 1


def _maybe_run_in_process() -> None:
    """Crutch for torch MPS-backend memory leak."""
    match torch.backends.mps.is_available():
        case True:
            sys.exit(_run_in_process())
        case False:
            sys.exit(uvloop.run(_run()))


def run() -> None:
    """Run POptimizer.

    Can be stopped with Ctrl-C/SIGINT. Settings from .env.
    """
    _maybe_run_in_process()
