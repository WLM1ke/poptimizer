from datetime import date

import aiohttp
import aiomoex
from pydantic import Field, TypeAdapter, field_validator

from poptimizer.core import domain, errors
from poptimizer.data import data, trading_day


class _Row(data.Row):
    day: domain.Day = Field(alias="begin")
    open: float = Field(alias="open", gt=0)
    close: float = Field(alias="close", gt=0)
    high: float = Field(alias="high", gt=0)
    low: float = Field(alias="low", gt=0)
    turnover: float = Field(alias="value", gt=0)


class USD(domain.Entity):
    df: list[_Row] = Field(default_factory=list[_Row])

    def update(self, update_day: domain.Day, rows: list[_Row]) -> None:
        self.day = update_day

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


class USDUpdated(domain.Event):
    day: domain.Day


class USDEventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._session = http_client

    async def handle(self, ctx: domain.Ctx, event: trading_day.TradingDayEnded) -> None:
        table = await ctx.get(USD)

        start_day = table.last_row_date()
        update_day = event.day
        rows = await self._download(start_day, update_day)

        table.update(update_day, rows)
        ctx.publish(USDUpdated(day=update_day))

    async def _download(
        self,
        start_day: date | None,
        update_day: date,
    ) -> list[_Row]:
        json = await aiomoex.get_market_candles(
            session=self._session,
            start=start_day and str(start_day),
            end=str(update_day),
            interval=24,
            security="USD000UTSTOM",
            market="selt",
            engine="currency",
        )

        return TypeAdapter(list[_Row]).validate_python(json)
