import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.cli import safe
from poptimizer.reports.metrics import plot


async def _run() -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        lgr = await stack.enter_async_context(logger.init())

        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        repo = mongo.Repo(mongo_db)

        await safe.run(lgr, plot(repo))


def metrics() -> None:
    """Plot all models metrics."""
    uvloop.run(_run())
