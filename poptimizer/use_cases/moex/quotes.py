import asyncio
from datetime import date

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.moex import quotes, securities
from poptimizer.use_cases import handler


class QuotesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.DivUpdated) -> handler.QuotesUpdated:
        sec_table = await ctx.get(securities.Securities)

        trading_days: set[domain.Day] = set()

        async with asyncio.TaskGroup() as tg:
            for sec in sec_table.df:
                tg.create_task(self._update_one(ctx, sec.ticker, msg.day, trading_days))

        sorted_trading_days = sorted(trading_days)
        if msg.day != sorted_trading_days[-1]:
            raise errors.UseCasesError("no quotes for last trading day")

        return handler.QuotesUpdated(trading_days=sorted_trading_days)

    async def _update_one(
        self,
        ctx: handler.Ctx,
        ticker: str,
        update_day: domain.Day,
        trading_days: set[domain.Day],
    ) -> None:
        table = await ctx.get_for_update(quotes.Quotes, domain.UID(ticker))

        start_day = table.last_row_date() or consts.START_DAY
        rows = await self._download(ticker, start_day, update_day)

        table.update(update_day, rows)

        trading_days.update(row.day for row in table.df)

    async def _download(
        self,
        ticker: str,
        start_day: date | None,
        update_day: domain.Day,
    ) -> list[quotes.Row]:
        try:
            json = await aiomoex.get_market_candles(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(update_day),
                interval=24,
                security=ticker,
                market="shares",
                engine="stock",
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError(f"{ticker} MOEX ISS error") from err

        try:
            return TypeAdapter(list[quotes.Row]).validate_python(json)
        except ValueError as err:
            raise errors.UseCasesError(f"invalid {ticker} data") from err
