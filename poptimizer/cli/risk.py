import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.controllers.reports.risk import report


async def _run(months: int) -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        lgr = await stack.enter_async_context(logger.init())
        repo = mongo.Repo(mongo_db)

        try:
            await report(repo, months)
        except asyncio.CancelledError:
            lgr.info("Stopped")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def risk(months: int) -> None:
    """Risk-return analysis."""
    uvloop.run(_run(months))
