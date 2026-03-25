import asyncio
import contextlib
import multiprocessing as mp
import signal
import sys
from types import FrameType
from typing import TYPE_CHECKING, Any

import torch
import uvloop

from poptimizer.adapters import gmail, http_session, logger, mongo
from poptimizer.adapters.brokers import tinkoff
from poptimizer.cli import config, safe
from poptimizer.controllers.bus import bus
from poptimizer.controllers.server import server

if TYPE_CHECKING:
    from collections.abc import Callable


class _SignalHandler:
    def __init__(self, task: asyncio.Task[Any]) -> None:
        self._task = task

    def __call__(self, sig: int, frame: FrameType | None) -> None:  # noqa: ARG002
        self._task.cancel()


class Run(config.Cfg):
    """Run POptimizer - can be stopped with Ctrl-C/SIGINT."""

    def cli_cmd(self) -> None:
        """Crutch for torch MPS-backend memory leak."""
        match torch.backends.mps.is_available():
            case True:
                sys.exit(self._run_in_process())
            case False:
                sys.exit(uvloop.run(self._run()))

    def _run_in_process(self) -> int:
        stopping = False

        while True:
            process = mp.Process(target=self._run_in_uvloop, daemon=True)
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

    def _run_in_uvloop(self) -> None:
        with (
            asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner,
            contextlib.suppress(asyncio.CancelledError),
        ):
            sys.exit(runner.run(self._run(check_memory=True)))

    async def _run(self, *, check_memory: bool = False) -> int:
        stop_fn: Callable[[], bool] | None = None
        if check_memory and (main_task := asyncio.current_task()):
            signal.signal(signal.SIGTERM, _SignalHandler(main_task))
            stop_fn = main_task.cancel

        async with contextlib.AsyncExitStack() as stack:
            http_client = await stack.enter_async_context(http_session.client())
            tinkoff_client = tinkoff.Client(http_client, self.brokers.tinkoff)
            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))

            send_fn: Callable[[str], None] | None = None
            if self.gmail.email and self.gmail.password:
                gmail_sender = await stack.enter_async_context(gmail.Sender(self.gmail.email, self.gmail.password))
                send_fn = gmail_sender.send

            lgr = await stack.enter_async_context(logger.init(send_fn))

            msg_bus = bus.build(lgr, http_client, tinkoff_client, mongo_db, stop_fn)

            return await safe.run(
                lgr,
                msg_bus.run(),
                server.run(lgr, self.server.url, msg_bus),
            )

        return 1
