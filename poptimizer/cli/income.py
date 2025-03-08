import asyncio
import contextlib
from typing import Annotated

import typer
import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.domain.funds import funds
from poptimizer.reports.income import report


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


def income(
    investor: Annotated[
        str,
        typer.Argument(help="Investor name", show_default=False),
    ],
    months: Annotated[
        int,
        typer.Argument(help="Last months to report", show_default=False, min=1),
    ],
) -> None:
    """Print CPI-adjusted income report."""
    uvloop.run(_run(funds.Investor(investor), months))
