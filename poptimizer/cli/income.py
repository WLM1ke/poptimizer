import contextlib

from pydantic import Field
from pydantic_settings import CliPositionalArg

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.domain.funds import funds
from poptimizer.reports.income import report


class Income(config.Cfg):
    """Print CPI-adjusted income report."""

    investor: CliPositionalArg[funds.Investor] = Field(description="Investor name")
    months: CliPositionalArg[int] = Field(ge=1, description="Last months to report")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            lgr = await stack.enter_async_context(logger.init())
            repo = mongo.Repo(mongo_db)

            await safe.run(lgr, report(repo, self.investor, self.months))
