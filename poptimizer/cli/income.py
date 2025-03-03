import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.controllers.reports.income import report
from poptimizer.domain.funds import funds


async def _run(investor: funds.Investor, months: int) -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        lgr = await stack.enter_async_context(logger.init())
        repo = mongo.Repo(mongo_db)

        try:
            await report(repo, investor, months)
        except asyncio.CancelledError:
            lgr.info("Stopped")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def income(investor: str, months: int) -> None:
    """CPI-adjusted income report."""
    uvloop.run(_run(funds.Investor(investor), months))
