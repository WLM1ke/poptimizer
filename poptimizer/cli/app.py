import asyncio
import contextlib
import multiprocessing as mp
import signal
import sys
from types import FrameType
from typing import TYPE_CHECKING, Any

import torch
import uvloop

from poptimizer import config
from poptimizer.adapters import http_session, logger, mongo
from poptimizer.cli import safe
from poptimizer.controllers.bus import bus
from poptimizer.controllers.server import server
from poptimizer.controllers.tg import tg

if TYPE_CHECKING:
    from collections.abc import Callable


class _SignalHandler:
    def __init__(self, task: asyncio.Task[Any]) -> None:
        self._task = task

    def __call__(self, sig: int, frame: FrameType | None) -> None:  # noqa: ARG002
        self._task.cancel()


async def _run(*, check_memory: bool = False) -> int:
    cancel_fn: Callable[[], bool] | None = None
    if check_memory and (main_task := asyncio.current_task()):
        signal.signal(signal.SIGTERM, _SignalHandler(main_task))
        cancel_fn = main_task.cancel

    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http_session.client())
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))

        lgr = await stack.enter_async_context(
            logger.init(
                http_client,
                cfg.telegram_token,
                cfg.telegram_chat_id,
            )
        )

        msg_bus = bus.build(http_client, mongo_db, cancel_fn)
        http_server = server.Server(cfg.server_url, msg_bus)
        bot = tg.Bot(cfg.telegram_token, cfg.telegram_chat_id, mongo_db, msg_bus)

        return await safe.run(
            lgr,
            msg_bus.run(),
            http_server.run(),
            bot.run(),
        )

    return 1


def _run_in_uvloop() -> None:
    with (
        asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner,
        contextlib.suppress(asyncio.CancelledError),
    ):
        sys.exit(runner.run(_run(check_memory=True)))


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
