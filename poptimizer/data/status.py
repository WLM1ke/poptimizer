import csv
import io
import itertools
import re
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from typing import Final

import aiohttp
from pydantic import Field, field_validator

from poptimizer.core import domain, errors
from poptimizer.data import data, securities

_URL: Final = "https://web.moex.com/moex-web-icdb-api/api/v1/export/site-register-closings/csv?separator=1&language=1"
_LOOK_BACK_DAYS: Final = 14
_DATE_FMT: Final = "%m/%d/%Y %H:%M:%S"
_RE_TICKER = re.compile(r", ([A-Z]+-[A-Z]+|[A-Z]+) \[")


class _Row(data.Row):
    ticker: str
    ticker_base: str
    preferred: bool
    day: domain.Day


class DivStatus(domain.Entity):
    df: list[_Row] = Field(default_factory=list[_Row])

    def update(self, update_day: domain.Day, rows: list[_Row]) -> None:
        self.timestamp = update_day

        rows.sort(key=(lambda status: (status.ticker, status.day)))

        self.df = rows

    @field_validator("df")
    def _must_be_sorted_by_ticker_and_day(cls, df: list[_Row]) -> list[_Row]:
        ticker_date_pairs = itertools.pairwise((row.ticker, row.day) for row in df)

        if not all(ticker_date <= next_ for ticker_date, next_ in ticker_date_pairs):
            raise ValueError("ticker and dates are not sorted")

        return df


class DivStatusUpdated(domain.Event):
    day: domain.Day


class DivStatusEventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def handle(self, ctx: domain.Ctx, event: securities.SecuritiesUpdated) -> None:
        sec_table = await ctx.get(securities.Securities, for_update=False)
        table = await ctx.get(DivStatus)
        csv_file = await self._download()
        parsed_rows = self._parse(ctx, csv_file, sec_table)

        update_day = event.day
        table.update(update_day, parsed_rows)
        ctx.publish(DivStatusUpdated(day=update_day))

    async def _download(self) -> io.StringIO:
        async with self._http_client.get(_URL) as resp:
            if not resp.ok:
                raise errors.DomainError(f"bad dividends status respond {resp.reason}")

            return io.StringIO(await resp.text(encoding="cp1251"), newline="")

    def _parse(
        self,
        ctx: domain.Ctx,
        csv_file: io.StringIO,
        sec: securities.Securities,
    ) -> list[_Row]:
        reader = csv.reader(csv_file)
        next(reader)

        return list(_status_gen(self._parsed_rows_gen(ctx, reader), sec))

    def _parsed_rows_gen(
        self,
        ctx: domain.Ctx,
        reader: Iterator[list[str]],
    ) -> Iterator[tuple[str, date]]:
        for ticker_raw, date_raw, *_ in reader:
            timestamp = datetime.strptime(date_raw, _DATE_FMT)
            day = date(timestamp.year, timestamp.month, timestamp.day)

            if day < date.today() - timedelta(days=_LOOK_BACK_DAYS):
                continue

            if (ticker_re := _RE_TICKER.search(ticker_raw)) is None:
                ctx.publish_err(f"can't parse ticker from {ticker_raw}")

                continue

            yield ticker_re[1], day


def _status_gen(
    raw_rows: Iterator[tuple[str, date]],
    sec: securities.Securities,
) -> Iterator[_Row]:
    sec_map = {row.ticker: row for row in sec.df}
    for ticker, day in raw_rows:
        sec_desc = sec_map.get(ticker)
        if sec_desc and sec_desc.is_share:
            yield _Row(
                ticker=ticker,
                ticker_base=sec_desc.ticker_base,
                preferred=sec_desc.is_preferred,
                day=day,
            )
