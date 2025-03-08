import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.reports.stats import report


async def _run() -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        lgr = await stack.enter_async_context(logger.init())

        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        repo = mongo.Repo(mongo_db)

        try:
            await report(repo)
        except asyncio.CancelledError:
            lgr.info("Shutdown finished")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def stats() -> None:
    """Print current evolution statistics."""
    uvloop.run(_run())
