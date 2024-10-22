from datetime import date

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer import errors
from poptimizer.domain.data import usd
from poptimizer.handlers import handler


class USDHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._session = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.IndexesUpdated) -> None:
        table = await ctx.get_for_update(usd.USD)

        start_day = table.last_row_date()
        rows = await self._download(start_day, msg.day)

        table.update(msg.day, rows)
        ctx.publish(handler.USDUpdated(day=msg.day))

    async def _download(
        self,
        start_day: date | None,
        update_day: date,
    ) -> list[usd.Row]:
        try:
            json = await aiomoex.get_market_candles(
                session=self._session,
                start=start_day and str(start_day),
                end=str(update_day),
                interval=24,
                security="USD000UTSTOM",
                market="selt",
                engine="currency",
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.HandlerError("usd MOEX ISS error") from err

        try:
            return TypeAdapter(list[usd.Row]).validate_python(json)
        except ValueError as err:
            raise errors.HandlerError("invalid usd data") from err
