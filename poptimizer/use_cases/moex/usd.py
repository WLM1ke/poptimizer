from datetime import date

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer.domain.moex import usd
from poptimizer.use_cases import handler


class USDHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._session = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.NewDataPublished) -> None:
        table = await ctx.get_for_update(usd.USD)

        start_day = table.last_row_date()
        rows = await self._download(start_day, msg.day)

        table.update(msg.day, rows)

    async def _download(
        self,
        start_day: date | None,
        update_day: date,
    ) -> list[usd.Row]:
        async with handler.wrap_http_err("USD MOEX ISS error"):
            json = await aiomoex.get_market_candles(
                session=self._session,
                start=start_day and str(start_day),
                end=str(update_day),
                interval=24,
                security="USD000UTSTOM",
                market="selt",
                engine="currency",
            )

        with handler.wrap_validation_err("invalid USD data"):
            return TypeAdapter(list[usd.Row]).validate_python(json)
