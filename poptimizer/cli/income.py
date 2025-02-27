import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.domain import cpi
from poptimizer.domain.reports import funds
from poptimizer.domain.reports.income import report


async def _run(investor: funds.Investor, months: int) -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        lgr = await stack.enter_async_context(logger.init())
        repo = mongo.Repo(mongo_db)

        lgr.info("CPI-adjusted report for %s", investor)

        try:
            fund = await repo.get(funds.Fund)
            cpi_table = await repo.get(cpi.CPI)
            rows = report(fund, cpi_table, months, investor)

            for row in rows:
                lgr.info(row)
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
