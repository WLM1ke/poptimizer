import asyncio
import contextlib
import multiprocessing as mp
import sys
from collections.abc import Callable, Coroutine

import torch
import uvloop

from poptimizer.adapters import gmail, http, logger, mongo
from poptimizer.cli import config, safe
from poptimizer.data import data
from poptimizer.data.clients import data as data_client
from poptimizer.data.clients import memory, migration
from poptimizer.evolve import evolve
from poptimizer.forecast import forecast
from poptimizer.fsm import system, tx
from poptimizer.portfolio import portfolio
from poptimizer.portfolio.clients import tinkoff
from poptimizer.views.web import server


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
        async with contextlib.AsyncExitStack() as stack:
            http_client = await stack.enter_async_context(http.client())
            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))

            send_fn: Callable[[str], None] | None = None
            coro: list[Coroutine[None, None, None]] = []
            if self.gmail.email and self.gmail.password:
                gmail_sender = await stack.enter_async_context(gmail.Sender(self.gmail.email, self.gmail.password))
                send_fn = gmail_sender.send
                coro.append(gmail_sender.run())

            lgr = logger.init(send_fn)

            repo = mongo.Repo(mongo_db)

            main_task = None

            if check_memory:
                main_task = asyncio.current_task()

            dispatcher = tx.Dispatcher()

            fsm_system = system.FSMSystem(repo, dispatcher)
            coro.append(
                fsm_system.start(
                    data.build_graph(
                        migration.Client(),
                        data_client.Client(http_client),
                        memory.Checker(main_task),
                    ),
                    portfolio.build_graph(
                        tinkoff.Client(http_client, self.brokers.tinkoff),
                    ),
                    evolve.build_graph(),
                    forecast.build_graph(),
                )
            )
            coro.append(server.run(repo, dispatcher, self.server.url))

            await safe.run(lgr, *coro)

        return 0


if __name__ == "__main__":
    Run().cli_cmd()
