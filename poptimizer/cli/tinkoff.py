import contextlib
import logging

from pydantic import BaseModel, Field
from pydantic_settings import CliPositionalArg

from poptimizer.adapters import http, logger
from poptimizer.cli import safe
from poptimizer.portfolio.clients import tinkoff


class Tinkoff(BaseModel):
    """Get Tinkoff accounts info."""

    token: CliPositionalArg[str] = Field(description="Tinkoff API token")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            http_client = await stack.enter_async_context(http.client())
            tinkoff_client = tinkoff.Client(http_client, [])

            await safe.run(logger.init(), self._run(logger.init(), tinkoff_client))

    async def _run(self, lgr: logging.Logger, tinkoff_client: tinkoff.Client) -> None:
        accounts = await tinkoff_client.get_accounts(self.token)

        lgr.info("Tinkoff accounts:")

        for n, account in enumerate(accounts, 1):
            lgr.info('%d. %s - id="%s"', n, account.name, account.id)
