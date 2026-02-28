import asyncio
import bisect
import itertools
from typing import Annotated, Protocol

from pydantic import AfterValidator, Field, PositiveFloat

from poptimizer.core import domain, errors, fsms
from poptimizer.data.div import status
from poptimizer.data.moex import quotes


class Row(domain.Row):
    day: domain.Day
    dividend: PositiveFloat

    def to_tuple(self) -> tuple[domain.Day, float]:
        return self.day, self.dividend


def _sorted_by_date_and_div(df: list[Row]) -> list[Row]:
    day_pairs = itertools.pairwise(row.to_tuple() for row in df)

    if not all(day <= next_ for day, next_ in day_pairs):
        raise ValueError("raw dividends are not sorted")

    return df


class DivRaw(domain.Entity):
    df: Annotated[
        list[Row],
        AfterValidator(_sorted_by_date_and_div),
        AfterValidator(domain.after_start_date_validator),
    ] = Field(default_factory=list[Row])

    def update(self, rows: list[Row]) -> None:
        self.df = sorted(rows, key=lambda row: row.to_tuple())

    def add_row(self, row: Row) -> None:
        self.df.append(row)
        self.df = sorted(self.df, key=lambda row: row.to_tuple())

    def remove_row(self, row: Row) -> None:
        try:
            self.df.remove(row)
        except ValueError as err:
            raise errors.DomainError("dividend not found") from err

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


class DivReestry(DivRaw): ...


class Client(Protocol):
    async def get_divs(self, start_day: domain.Day, row: status.Row) -> list[Row]: ...


async def update(ctx: fsms.Ctx, web_client: Client) -> None:
    status_table = await ctx.get(status.DivStatus)

    async with asyncio.TaskGroup() as tg:
        for row in status_table.df:
            tg.create_task(_update_one(ctx, web_client, row))


async def _update_one(
    ctx: fsms.Ctx,
    web_client: Client,
    status_row: status.Row,
) -> None:
    div_table = await ctx.get_for_update(DivReestry, domain.UID(status_row.ticker))

    if div_table.has_day(status_row.day):
        return

    quotes_table = await ctx.get_for_update(quotes.Quotes, domain.UID(status_row.ticker))

    rows = await web_client.get_divs(quotes_table.df[0].day, status_row)

    div_table.update(rows)
