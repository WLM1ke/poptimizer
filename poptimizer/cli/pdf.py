import asyncio
import contextlib
from datetime import date

import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.controllers.reports.pdf import pdf
from poptimizer.domain.funds import funds


async def _run(
    day: date,
    dividends: float,
    inflows: dict[str, float],
) -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        lgr = await stack.enter_async_context(logger.init())

        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        repo = mongo.Repo(mongo_db)

        try:
            await pdf.report(
                repo,
                day,
                dividends,
                {funds.Investor(investor): value for investor, value in inflows.items()},
            )
        except asyncio.CancelledError:
            lgr.info("Shutdown finished")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def report(
    day: date,
    dividends: float,
    inflows: dict[str, float],
) -> None:
    """Fund pdf report for 5 years."""
    uvloop.run(_run(day, dividends, inflows))


if __name__ == "__main__":
    report(date(2025, 3, 5), 0.0, {"Mike": -1_000_000})
