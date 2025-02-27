import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.domain.moex import index
from poptimizer.domain.reports import funds
from poptimizer.domain.reports.risk import report


async def _run(months: int) -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        lgr = await stack.enter_async_context(logger.init())
        repo = mongo.Repo(mongo_db)

        lgr.info("Risk-return analysis for %dM", months)

        try:
            fund = await repo.get(funds.Fund)
            index_table = await repo.get(index.Index, index.MCFTRR)
            rf_table = await repo.get(index.Index, index.RUGBITR1Y)
            rows = report(fund, index_table, rf_table, months)

            for row in rows:
                lgr.info(row)
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
