import asyncio
import bisect
import itertools

from pydantic import Field, field_validator

from poptimizer.core import consts, domain
from poptimizer.data import data, status


class Row(data.Row):
    day: domain.Day
    dividend: float = Field(gt=0)
    currency: domain.Currency

    def to_tuple(self) -> tuple[domain.Day, float, domain.Currency]:
        return self.day, self.dividend, self.currency

    def is_valid_date(self) -> bool:
        return self.day >= consts.START_DAY


class DivRaw(domain.Entity):
    df: list[Row] = Field(default_factory=list[Row])

    def update(self, update_day: domain.Day, rows: list[Row]) -> None:
        self.day = update_day

        rows.sort(key=lambda row: row.to_tuple())

        self.df = rows

    def has_day(self, day: domain.Day) -> bool:
        pos = bisect.bisect_left(self.df, day, key=lambda row: row.day)

        return pos != len(self.df) and self.df[pos].day == day

    def has_row(self, row: Row) -> bool:
        pos = bisect.bisect_left(
            self.df,
            row.to_tuple(),
            key=lambda row: row.to_tuple(),
        )

        return pos != len(self.df) and row == self.df[pos]

    @field_validator("df")
    def _sorted_by_date_div_currency(cls, df: list[Row]) -> list[Row]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in df)

        if not all(day < next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return df


class RawDividendsChecked(domain.Event):
    day: domain.Day


class CheckRawDividendsEventHandler:
    async def handle(self, ctx: domain.Ctx, event: status.DivStatusUpdated) -> None:
        status_table = await ctx.get(status.DivStatus, for_update=False)

        async with asyncio.TaskGroup() as tg:
            for row in status_table.df:
                tg.create_task(self._check_one(ctx, row))

        ctx.publish(RawDividendsChecked(day=event.day))

    async def _check_one(self, ctx: domain.Ctx, row: status.Row) -> None:
        table = await ctx.get(DivRaw, domain.UID(row.ticker), for_update=False)

        if not table.has_day(row.day):
            ctx.warn(f"{row.ticker} missed dividend at {row.day}")
