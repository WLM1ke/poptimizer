import contextlib

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.fsm import uow
from poptimizer.reports.metrics import plot


class Metrics(config.Cfg):
    """Plot all models metrics."""

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = logger.init()

            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            repo = mongo.Repo(mongo_db)

            await safe.run(lgr, plot(uow.UOW(repo)))
