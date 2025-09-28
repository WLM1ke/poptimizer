import asyncio
from datetime import date, timedelta

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.moex import index
from poptimizer.use_cases import handler


class IndexesHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.QuotesUpdated) -> handler.IndexesUpdated:
        async with asyncio.TaskGroup() as tg:
            for ticker in index.INDEXES:
                tg.create_task(self._update_one(ctx, msg.day, ticker))

        imoex = await ctx.get(index.Index, index.IMOEX)

        return handler.IndexesUpdated(trading_days=[row.day for row in imoex.df if row.day >= consts.START_DAY])

    async def _update_one(self, ctx: handler.Ctx, update_day: domain.Day, ticker: domain.UID) -> None:
        table = await ctx.get_for_update(index.Index, ticker)

        if ticker == index.IMOEX:
            ticker = index.IMOEX2

        start_day = table.last_row_date()
        rows = await self._download(ticker, start_day, update_day)

        if start_day is None and ticker == index.IMOEX2:
            first_rows = await self._download(index.IMOEX, None, rows[0].day - timedelta(days=1))
            rows = first_rows + rows

        table.update(update_day, rows)

    async def _download(
        self,
        ticker: str,
        start_day: date | None,
        update_day: date,
    ) -> list[index.Row]:
        async with handler.wrap_http_err(f"{ticker} MOEX ISS error"):
            json = await aiomoex.get_market_candles(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(update_day),
                interval=24,
                security=ticker,
                market="index",
                engine="stock",
            )

        with handler.wrap_validation_err(f"invalid {ticker} data"):
            return TypeAdapter(list[index.Row]).validate_python(json)
