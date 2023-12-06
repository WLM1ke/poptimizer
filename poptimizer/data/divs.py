import asyncio
import bisect
import datetime
import itertools
from collections.abc import Iterator
from datetime import date
from typing import Final

from pydantic import Field, field_validator

from poptimizer.core import consts, domain
from poptimizer.data import data, securities, usd

_MIN_DATE: Final = datetime.datetime(datetime.MINYEAR, 1, 1)


class _RawRow(data.Row):
    day: domain.Day
    dividend: float = Field(gt=0)
    currency: domain.Currency

    def to_tuple(self) -> tuple[domain.Day, float, domain.Currency]:
        return self.day, self.dividend, self.currency

    def is_valid_date(self) -> bool:
        return self.day >= consts.START_DAY


class RawDividends(domain.Entity):
    df: list[_RawRow] = Field(default_factory=list[_RawRow])

    def update(self, update_day: domain.Day, rows: list[_RawRow]) -> None:
        self.timestamp = update_day

        rows.sort(key=lambda row: row.to_tuple())

        self.df = rows

    def has_date(self, day: domain.Day) -> bool:
        pos = bisect.bisect_left(self.df, day, key=lambda row: row.day)

        return pos != len(self.df) and self.df[pos].day == day

    def has_row(self, raw_row: _RawRow) -> bool:
        pos = bisect.bisect_left(
            self.df,
            raw_row.to_tuple(),
            key=lambda row: row.to_tuple(),
        )

        return pos != len(self.df) and raw_row == self.df[pos]

    @field_validator("df")
    def _sorted_by_date_div_currency(cls, df: list[_RawRow]) -> list[_RawRow]:
        day_pairs = itertools.pairwise(row.to_tuple() for row in df)

        if not all(day < next_ for day, next_ in day_pairs):
            raise ValueError("raw dividends are not sorted")

        return df


class _Row(data.Row):
    day: domain.Day
    dividend: float = Field(gt=0)


class Dividends(domain.Entity):
    df: list[_Row] = Field(default_factory=list[_Row])

    def update(self, update_day: domain.Day, rows: list[_Row]) -> None:
        self.timestamp = update_day
        self.df = rows

    _must_be_sorted_by_date = field_validator("df")(data.sorted_by_day_validator)
    _must_be_after_start_date = field_validator("df")(data.after_start_date_validator)


class DividendsUpdated(domain.Event):
    day: domain.Day


class DividendsEventHandler:
    def __init__(self) -> None:
        self._securities_day = _MIN_DATE
        self._usd_day = _MIN_DATE

    async def handle(self, ctx: domain.Ctx, event: usd.USDUpdated | securities.SecuritiesUpdated) -> None:
        match event:
            case usd.USDUpdated():
                self._usd_day = event.day
            case securities.SecuritiesUpdated():
                self._securities_day = event.day

        if self._usd_day == self._securities_day:
            await self._update(ctx, event.day)

    async def _update(self, ctx: domain.Ctx, update_day: domain.Day) -> None:
        usd_table = await ctx.get(usd.USD)
        sec_table = await ctx.get(securities.Securities)

        async with asyncio.TaskGroup() as tg:
            for sec in sec_table.df:
                tg.create_task(self._update_one(ctx, update_day, domain.UID(sec.ticker), usd_table))

        ctx.publish(DividendsUpdated(day=update_day))

    async def _update_one(self, ctx: domain.Ctx, update_day: date, ticker: domain.UID, usd_table: usd.USD) -> None:
        div_table = await ctx.get(Dividends, ticker)
        raw_table = await ctx.get(RawDividends, ticker)

        rows = list(_prepare_rows(raw_table.df, usd_table))

        div_table.update(update_day, rows)


def _prepare_rows(
    raw_list: list[_RawRow],
    usd_table: usd.USD,
) -> Iterator[_Row]:
    div = 0
    date = _MIN_DATE
    if raw_list:
        date = raw_list[0].day

    for row in raw_list:
        if row.day > date:
            yield _Row(day=date, dividend=div)

            date = row.day
            div = 0

        div += _div_in_rur(row, usd_table)

    if div:
        yield _Row(day=date, dividend=div)


def _div_in_rur(raw_row: _RawRow, usd_table: usd.USD) -> float:
    match raw_row.currency:
        case domain.Currency.RUR:
            return raw_row.dividend
        case domain.Currency.USD:
            pos = bisect.bisect_right(usd_table.df, raw_row.day, key=lambda usd_row: usd_row.day)

            return raw_row.dividend * usd_table.df[pos - 1].close
