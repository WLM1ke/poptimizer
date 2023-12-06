import asyncio
from datetime import date
from typing import Final

import aiohttp
import aiomoex
from pydantic import Field, TypeAdapter, field_validator

from poptimizer.core import domain, errors
from poptimizer.data import data, trading_day

_INDEXES: Final = (
    domain.UID("MCFTRR"),
    domain.UID("MEOGTRR"),
    domain.UID("IMOEX"),
    domain.UID("RVI"),
)


class _Row(data.Row):
    day: domain.Day = Field(alias="TRADEDATE")
    close: float = Field(alias="CLOSE", gt=0)


class Index(domain.Entity):
    df: list[_Row] = Field(default_factory=list[_Row])

    def update(self, update_day: domain.Day, rows: list[_Row]) -> None:
        self.timestamp = update_day

        if not self.df:
            self.df = rows

            return

        last = self.df[-1]

        if last != (first := rows[0]):
            raise errors.DomainError(f"{self.uid} data mismatch {last} vs {first}")

        self.df.extend(rows[1:])

    def last_row_date(self) -> date | None:
        if not self.df:
            return None

        return self.df[-1].day

    _must_be_sorted_by_date = field_validator("df")(data.sorted_by_day_validator)


class IndexesUpdated(domain.Event):
    day: domain.Day


class IndexesEventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def handle(self, ctx: domain.Ctx, event: trading_day.TradingDayEnded) -> None:
        async with asyncio.TaskGroup() as tg:
            for index in _INDEXES:
                tg.create_task(self._update_one(ctx, event.day, index))

        ctx.publish(IndexesUpdated(day=event.day))

    async def _update_one(self, ctx: domain.Ctx, update_day: domain.Day, index: domain.UID) -> None:
        table = await ctx.get(Index, index)

        start_day = table.last_row_date()
        rows = await self._download(index, start_day, update_day)

        table.update(update_day, rows)

    async def _download(
        self,
        index: str,
        start_day: date | None,
        update_day: date,
    ) -> list[_Row]:
        json = await aiomoex.get_market_history(
            session=self._http_client,
            start=start_day and str(start_day),
            end=str(update_day),
            security=index,
            columns=(
                "TRADEDATE",
                "CLOSE",
            ),
            market="index",
        )

        return TypeAdapter(list[_Row]).validate_python(json)
