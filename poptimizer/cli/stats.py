import contextlib

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.reports.stats import report
from poptimizer.runtime import uow


class Stats(config.Cfg):
    """Print current evolution statistics."""

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = logger.init()

            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            store = mongo.Store(mongo_db)

            async with uow.UOW(store) as repo:
                await safe.run(lgr, report(lgr, repo))
