import asyncio
from datetime import date

import aiohttp
import aiomoex
from pydantic import Field, TypeAdapter, field_validator

from poptimizer.core import consts, domain, errors
from poptimizer.data import data, securities
from poptimizer.data.contracts import QuotesUpdated


class _Row(data.Row):
    day: domain.Day = Field(alias="begin")
    open: float = Field(alias="open", gt=0)
    close: float = Field(alias="close", gt=0)
    high: float = Field(alias="high", gt=0)
    low: float = Field(alias="low", gt=0)
    turnover: float = Field(alias="value", ge=0)


class Quotes(domain.Entity):
    df: list[_Row] = Field(default_factory=list[_Row])

    def update(self, update_day: domain.Day, rows: list[_Row]) -> None:
        self.day = update_day

        if not self.df:
            rows.sort(key=lambda row: row.day)
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
    _must_be_after_start_date = field_validator("df")(data.after_start_date_validator)


class QuotesEventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def handle(self, ctx: domain.Ctx, event: securities.SecuritiesUpdated) -> None:
        sec_table = await ctx.get(securities.Securities, for_update=False)
        update_day = event.day
        async with asyncio.TaskGroup() as tg:
            for sec in sec_table.df:
                tg.create_task(self._update_one(ctx, sec.ticker, update_day))

        ctx.publish(QuotesUpdated(day=update_day))

    async def _update_one(
        self,
        ctx: domain.Ctx,
        ticker: str,
        update_day: domain.Day,
    ) -> None:
        table = await ctx.get(Quotes, domain.UID(ticker))

        start_day = table.last_row_date() or consts.START_DAY
        rows = await self._download(ticker, start_day, update_day)

        table.update(update_day, rows)

    async def _download(
        self,
        ticker: str,
        start_day: date | None,
        update_day: domain.Day,
    ) -> list[_Row]:
        json = await aiomoex.get_market_candles(
            session=self._http_client,
            start=start_day and str(start_day),
            end=str(update_day),
            interval=24,
            security=ticker,
            market="shares",
            engine="stock",
        )

        return TypeAdapter(list[_Row]).validate_python(json)
