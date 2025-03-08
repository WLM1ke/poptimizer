import asyncio
import contextlib
from datetime import date, datetime
from typing import Annotated, Final

import typer
import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.domain.funds import funds
from poptimizer.reports.pdf.pdf import report

_AMOUNT_SEP: Final = ":"


async def _run(
    day: date,
    dividends: float,
    raw_inflows: list[str],
) -> None:
    cfg = config.Cfg()
    err: Exception | None = None

    async with contextlib.AsyncExitStack() as stack:
        lgr = await stack.enter_async_context(logger.init())

        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo_db_uri, cfg.mongo_db_db))
        repo = mongo.Repo(mongo_db)

        try:
            inflows = [inflow.split(_AMOUNT_SEP) for inflow in raw_inflows]

            await report(
                repo,
                day,
                dividends,
                {funds.Investor(investor): float(value) for investor, value in inflows},
            )
        except asyncio.CancelledError:
            lgr.info("Shutdown finished")
        except Exception as exc:  # noqa: BLE001
            lgr.warning("Shutdown abnormally: %r", exc)
            err = exc

    if err:
        raise err


def pdf(
    day: Annotated[
        datetime,
        typer.Argument(
            help="Day of new fund statistics and report",
            formats=["%Y-%m-%d"],
            show_default=False,
        ),
    ],
    inflows: Annotated[
        list[str],
        typer.Option(
            "--inflows",
            "-i",
            help="Fund inflows from last report date for investors formatted as <investor>:<value>",
            default_factory=list,
            show_default=False,
        ),
    ],
    dividends: Annotated[
        float,
        typer.Option(
            "--dividends",
            "-d",
            help="Dividends from last report date",
        ),
    ] = 0,
) -> None:
    """Add data to fund statistics and create pdf report for last 5 years."""
    uvloop.run(_run(day.date(), dividends, inflows))
