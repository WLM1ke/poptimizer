import contextlib

from pydantic import Field
from pydantic_settings import CliPositionalArg

from poptimizer.adapters import logger, mongo
from poptimizer.cli import config, safe
from poptimizer.reports.risk import report


class Risk(config.Cfg):
    """Print fund risk-return report for last months."""

    months: CliPositionalArg[int] = Field(ge=2, description="Last months to report")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            mongo_db = await stack.enter_async_context(mongo.db(self.mongo.uri, self.mongo.db))
            lgr = await stack.enter_async_context(logger.init())
            repo = mongo.Repo(mongo_db)

            await safe.run(lgr, report(repo, self.months))
