import asyncio
from datetime import date

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.moex import quotes, securities
from poptimizer.use_cases import handler


class QuotesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.DivUpdated) -> handler.QuotesUpdated:
        sec_table = await ctx.get(securities.Securities)

        async with asyncio.TaskGroup() as tg:
            for sec in sec_table.df:
                tg.create_task(self._update_one(ctx, sec.ticker, msg.day))

        return handler.QuotesUpdated(day=msg.day)

    async def _update_one(
        self,
        ctx: handler.Ctx,
        ticker: str,
        update_day: domain.Day,
    ) -> None:
        table = await ctx.get_for_update(quotes.Quotes, domain.UID(ticker))

        start_day = table.last_row_date() or consts.START_DAY
        rows = await self._download(ticker, start_day, update_day)

        table.update(update_day, rows)

    async def _download(
        self,
        ticker: str,
        start_day: date | None,
        update_day: domain.Day,
    ) -> list[quotes.Row]:
        async with handler.wrap_http_err(f"{ticker} MOEX ISS error"):
            json = await aiomoex.get_market_candles(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(update_day),
                interval=24,
                security=ticker,
                market="shares",
                engine="stock",
            )

        with handler.wrap_validation_err(f"invalid {ticker} data"):
            return TypeAdapter(list[quotes.Row]).validate_python(json)
