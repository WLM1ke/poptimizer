import contextlib

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.data.div import raw


class Reset(config.Cfg):
    """Delete dividends to reload from backup on next start."""

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))

            await safe.run(logger.init(), mongo.Repo(mongo_db).drop(raw.DivRaw))
