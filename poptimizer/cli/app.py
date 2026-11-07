import asyncio
import contextlib
import sys
from collections.abc import Callable, Coroutine

import uvloop

from poptimizer.adapters import gmail, http, logger, mongo
from poptimizer.cli import config, safe
from poptimizer.clients import data as data_client
from poptimizer.clients import migration, tinkoff
from poptimizer.data import data
from poptimizer.evolve import evolve
from poptimizer.evolve.dl import pool, worker
from poptimizer.forecast import forecast
from poptimizer.fsm import system, tx
from poptimizer.portfolio import portfolio
from poptimizer.views.web import server


class Run(config.Cfg):
    """Run POptimizer - can be stopped with Ctrl-C/SIGINT."""

    def cli_cmd(self) -> None:
        with contextlib.suppress(asyncio.CancelledError):
            sys.exit(uvloop.run(self._run()))

    async def _run(self) -> int:
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

            store = mongo.Store(mongo_db)

            runner = await stack.enter_async_context(pool.PoolTrainingRunner(worker.train_worker))

            dispatcher = tx.Dispatcher()

            tinkoff_client = tinkoff.Client(http_client, self.brokers.tinkoff)

            fsm_system = system.FSMSystem(store, dispatcher)
            coro.append(
                fsm_system.start(
                    data.build_graph(
                        migration.Client(),
                        data_client.Client(http_client),
                    ),
                    portfolio.build_graph(tinkoff_client),
                    evolve.build_graph(runner),
                    forecast.build_graph(),
                )
            )
            coro.append(server.run(store, dispatcher, self.server.url))

            await safe.run(lgr, *coro)

        return 0


if __name__ == "__main__":
    Run().cli_cmd()
