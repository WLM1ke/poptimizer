import asyncio
import contextlib
import multiprocessing as mp
import sys

import torch
import uvloop

from poptimizer.adapters import http, logger, mongo
from poptimizer.cli import config
from poptimizer.data import data, events
from poptimizer.data.clients import data as data_client
from poptimizer.data.clients import migration
from poptimizer.fsm import system
from poptimizer.portfolio import portfolio


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

    async def _run(self, *, check_memory: bool = False) -> int:  # noqa: ARG002
        async with contextlib.AsyncExitStack() as stack:
            http_client = await stack.enter_async_context(http.client())
            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            # tg_bot = await stack.enter_async_context(tg.Bot(self.tg.token, self.tg.chat_id))  # noqa: ERA001
            await stack.enter_async_context(logger.init())

            repo = mongo.Repo(mongo_db)

            # main_task = None  # noqa: ERA001

            # if check_memory:
            #     main_task = asyncio.current_task()  # noqa: ERA001

            async with system.FSMSystem(repo) as fsm_system:
                fsm_system.start_fsm(data.build_graph(migration.Client(), data_client.Client(http_client)))
                fsm_system.start_fsm(portfolio.build_graph())
                fsm_system.send(events.AppStarted())

        return 0


if __name__ == "__main__":
    Run().cli_cmd()
