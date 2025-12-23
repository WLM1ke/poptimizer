import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, migrations, mongo
from poptimizer.cli import safe


async def _run() -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        lgr = await stack.enter_async_context(logger.init())

        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo.uri, cfg.mongo.db))
        repo = mongo.Repo(mongo_db)
        migrations.MigrationsHandler(repo)

        await safe.run(lgr, migrations.MigrationsHandler(repo).restore())


def div() -> None:
    """Update dividends from backup."""
    uvloop.run(_run())
