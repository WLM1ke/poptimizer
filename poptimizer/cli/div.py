import contextlib

from poptimizer.adapters import logger, migrations, mongo
from poptimizer.cli import config, safe


class Div(config.Cfg):
    """Update dividends from backup."""

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())

            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            repo = mongo.Repo(mongo_db)
            migrations.MigrationsHandler(repo)

            await safe.run(lgr, migrations.MigrationsHandler(repo).restore())
