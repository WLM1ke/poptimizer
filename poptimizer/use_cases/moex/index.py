import asyncio
from datetime import date
from typing import Final

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer import errors
from poptimizer.domain import domain
from poptimizer.domain.moex import index
from poptimizer.use_cases import handler

_INDEXES: Final = (
    domain.UID("MCFTRR"),
    domain.UID("MEOGTRR"),
    domain.UID("IMOEX"),
    domain.UID("RVI"),
)


class IndexesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.NewDataPublished) -> handler.IndexesUpdated:
        async with asyncio.TaskGroup() as tg:
            for ticker in _INDEXES:
                tg.create_task(self._update_one(ctx, msg.day, ticker))

        return handler.IndexesUpdated(day=msg.day)

    async def _update_one(self, ctx: handler.Ctx, update_day: domain.Day, ticker: domain.UID) -> None:
        table = await ctx.get_for_update(index.Index, ticker)

        start_day = table.last_row_date()
        rows = await self._download(ticker, start_day, update_day)

        table.update(update_day, rows)

    async def _download(
        self,
        ticker: str,
        start_day: date | None,
        update_day: date,
    ) -> list[index.Row]:
        try:
            json = await aiomoex.get_market_history(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(update_day),
                security=ticker,
                columns=(
                    "TRADEDATE",
                    "CLOSE",
                ),
                market="index",
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError(f"{ticker} MOEX ISS error") from err

        try:
            return TypeAdapter(list[index.Row]).validate_python(json)
        except ValueError as err:
            raise errors.UseCasesError(f"invalid {ticker} data") from err
