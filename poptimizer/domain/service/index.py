import asyncio
from datetime import date
from typing import Final

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer.domain import consts
from poptimizer.domain.entity import entity, index
from poptimizer.domain.service import domain_service

_INDEXES: Final = (
    entity.UID("MCFTRR"),
    entity.UID("MEOGTRR"),
    entity.UID("IMOEX"),
    entity.UID("RVI"),
)


class IndexesUpdater:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: domain_service.Ctx, update_day: entity.Day) -> None:
        async with asyncio.TaskGroup() as tg:
            for ticker in _INDEXES:
                tg.create_task(self._update_one(ctx, update_day, ticker))

    async def _update_one(self, ctx: domain_service.Ctx, update_day: entity.Day, ticker: entity.UID) -> None:
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

        try:
            return TypeAdapter(list[index.Row]).validate_python(json)
        except ValueError as err:
            raise consts.DomainError(f"invalid {ticker} data") from err
