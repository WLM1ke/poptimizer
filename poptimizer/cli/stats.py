import contextlib

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.reports.stats import report


class Stats(config.Cfg):
    """Print current evolution statistics."""

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())

            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            repo = mongo.Repo(mongo_db)

            await safe.run(lgr, report(repo))
