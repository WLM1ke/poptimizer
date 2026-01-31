import contextlib

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.domain.div import raw


class Div(config.Cfg):
    """Delete dividends."""

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())
            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))

            await safe.run(lgr, mongo.Repo(mongo_db).drop(raw.DivRaw))
