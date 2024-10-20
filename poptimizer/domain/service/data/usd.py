from datetime import date

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer.domain import consts
from poptimizer.domain.entity_ import entity
from poptimizer.domain.entity_.data import usd
from poptimizer.domain.service import domain_service


class USDUpdateService:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._session = http_client

    async def __call__(self, ctx: domain_service.Ctx, update_day: entity.Day) -> None:
        table = await ctx.get_for_update(usd.USD)

        start_day = table.last_row_date()
        rows = await self._download(start_day, update_day)

        table.update(update_day, rows)

    async def _download(
        self,
        start_day: date | None,
        update_day: date,
    ) -> list[usd.Row]:
        json = await aiomoex.get_market_candles(
            session=self._session,
            start=start_day and str(start_day),
            end=str(update_day),
            interval=24,
            security="USD000UTSTOM",
            market="selt",
            engine="currency",
        )

        try:
            return TypeAdapter(list[usd.Row]).validate_python(json)
        except ValueError as err:
            raise consts.DomainError("invalid usd data") from err
