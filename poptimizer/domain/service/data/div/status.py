import csv
import io
import re
from collections.abc import AsyncIterator, Iterable
from datetime import date, datetime, timedelta
from typing import Final, TextIO

import aiohttp

from poptimizer.domain import consts
from poptimizer.domain.entity import entity, portfolio
from poptimizer.domain.entity.data import securities
from poptimizer.domain.entity.data.div import raw, status
from poptimizer.domain.service import domain_service

_URL: Final = "https://web.moex.com/moex-web-icdb-api/api/v1/export/site-register-closings/csv?separator=1&language=1"
_LOOK_BACK_DAYS: Final = 14
_DATE_FMT: Final = "%m/%d/%Y %H:%M:%S"
_RE_TICKER = re.compile(r", ([A-Z]+-[A-Z]+|[A-Z]+) \[")


class DivUpdateService:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: domain_service.Ctx, update_day: entity.Day) -> None:
        table = await ctx.get_for_update(status.DivStatus)

        csv_file = await self._download()
        parsed_rows = _parse(ctx, csv_file)

        sec_table = await ctx.get(securities.Securities)
        port = await ctx.get(portfolio.Portfolio)
        status_gen = _status_gen(parsed_rows, sec_table, port)

        table.update(update_day, [row async for row in _filter_missed(ctx, status_gen)])

    async def _download(self) -> TextIO:
        async with self._http_client.get(_URL) as resp:
            if not resp.ok:
                raise consts.DomainError(f"bad dividends status respond {resp.reason}")

            return io.StringIO(await resp.text(encoding="cp1251"), newline="")


def _parse(
    ctx: domain_service.Ctx,
    csv_file: TextIO,
) -> Iterable[tuple[entity.Ticker, date]]:
    reader = csv.reader(csv_file)
    next(reader)

    for ticker_raw, date_raw, *_ in reader:
        timestamp = datetime.strptime(date_raw, _DATE_FMT)
        day = date(timestamp.year, timestamp.month, timestamp.day)

        if day < date.today() - timedelta(days=_LOOK_BACK_DAYS):
            continue

        if (ticker_re := _RE_TICKER.search(ticker_raw)) is None:
            ctx.warn(f"can't parse ticker from {ticker_raw}")

            continue

        yield entity.Ticker(ticker_re[1]), day


def _status_gen(
    raw_rows: Iterable[tuple[entity.Ticker, date]],
    sec: securities.Securities,
    port: portfolio.Portfolio,
) -> Iterable[status.Row]:
    weights = port.get_non_zero_weights().positions
    sec_map = {row.ticker: row for row in sec.df if row.ticker in weights}
    for ticker, day in raw_rows:
        if sec_desc := sec_map.get(ticker):
            yield status.Row(
                ticker=ticker,
                ticker_base=sec_desc.ticker_base,
                preferred=sec_desc.is_preferred,
                day=day,
            )


async def _filter_missed(ctx: domain_service.Ctx, rows: Iterable[status.Row]) -> AsyncIterator[status.Row]:
    for row in rows:
        table = await ctx.get(raw.DivRaw, entity.UID(row.ticker))

        if not table.has_day(row.day):
            ctx.warn(f"{row.ticker} missed dividend at {row.day}")

            yield row
