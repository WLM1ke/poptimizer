import asyncio
from datetime import date

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer.domain import consts
from poptimizer.domain.entity import entity
from poptimizer.domain.entity.data import quotes, securities
from poptimizer.domain.service import domain_service


class UpdateService:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: domain_service.Ctx, update_day: entity.Day) -> None:
        sec_table = await ctx.get(securities.Securities)

        async with asyncio.TaskGroup() as tg:
            for sec in sec_table.df:
                tg.create_task(self._update_one(ctx, sec.ticker, update_day))

    async def _update_one(
        self,
        ctx: domain_service.Ctx,
        ticker: str,
        update_day: entity.Day,
    ) -> None:
        table = await ctx.get_for_update(quotes.Quotes, entity.UID(ticker))

        start_day = table.last_row_date() or consts.START_DAY
        rows = await self._download(ticker, start_day, update_day)

        table.update(update_day, rows)

    async def _download(
        self,
        ticker: str,
        start_day: date | None,
        update_day: entity.Day,
    ) -> list[quotes.Row]:
        json = await aiomoex.get_market_candles(
            session=self._http_client,
            start=start_day and str(start_day),
            end=str(update_day),
            interval=24,
            security=ticker,
            market="shares",
            engine="stock",
        )

        try:
            return TypeAdapter(list[quotes.Row]).validate_python(json)
        except ValueError as err:
            raise consts.DomainError(f"invalid {ticker} data") from err
