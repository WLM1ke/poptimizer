import contextlib
from datetime import date

from pydantic import Field
from pydantic_settings import CliPositionalArg

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.domain.funds import funds
from poptimizer.reports.pdf.pdf import report


class PDF(config.Cfg):
    """Add data to fund statistics and create pdf report for last 5 years."""

    day: CliPositionalArg[date] = Field(description="Day of new fund statistics and report")
    inflows: dict[str, float] = Field(
        default_factory=dict[str, float],
        description="Inflows from last report date for investors",
    )
    dividends: float = Field(default=0, description="Dividends from last report date")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())

            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            repo = mongo.Repo(mongo_db)

            inflows = {funds.Investor(investor): inflow for investor, inflow in self.inflows.items()}

            await safe.run(lgr, report(repo, self.day, self.dividends, inflows))
