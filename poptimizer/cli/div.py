import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import backup, logger, mongo
from poptimizer.cli import safe


async def _run() -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        lgr = await stack.enter_async_context(logger.init())

        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        repo = mongo.Repo(mongo_db)
        backup.BackupHandler(repo)

        await safe.run(lgr, backup.BackupHandler(repo).restore())


def div() -> None:
    """Update dividends from backup."""
    uvloop.run(_run())
