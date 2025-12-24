import contextlib
import logging

from pydantic import BaseModel, Field
from pydantic_settings import CliPositionalArg

from poptimizer.adapters import http_session, logger
from poptimizer.adapters.brokers import tinkoff
from poptimizer.cli import safe


class Tinkoff(BaseModel):
    """Get Tinkoff accounts info."""

    token: CliPositionalArg[str] = Field(description="Tinkoff API token")

    async def cli_cmd(self) -> None:
        async with contextlib.AsyncExitStack() as stack:
            lgr = await stack.enter_async_context(logger.init())
            http_client = await stack.enter_async_context(http_session.client())
            tinkoff_client = tinkoff.Client(http_client, [])

            await safe.run(lgr, self._run(lgr, tinkoff_client))

    async def _run(self, lgr: logging.Logger, tinkoff_client: tinkoff.Client) -> None:
        accounts = await tinkoff_client.get_accounts(self.token)

        lgr.info("Tinkoff accounts:")

        for n, account in enumerate(accounts, 1):
            lgr.info('%d. %s - id="%s"', n, account.name, account.id)
