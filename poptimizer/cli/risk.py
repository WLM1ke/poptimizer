import contextlib
from typing import Annotated

import typer
import uvloop

from poptimizer import config
from poptimizer.adapters import logger, mongo
from poptimizer.cli import safe
from poptimizer.reports.risk import report


async def _run(months: int) -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        mongo_db = await stack.enter_async_context(mongo.db(cfg.mongo.uri, cfg.mongo.db))
        lgr = await stack.enter_async_context(logger.init())
        repo = mongo.Repo(mongo_db)

        await safe.run(lgr, report(repo, months))


def risk(
    months: Annotated[
        int,
        typer.Argument(help="Last months to report", show_default=False, min=2),
    ],
) -> None:
    """Print fund risk-return report for last months."""
    uvloop.run(_run(months))
