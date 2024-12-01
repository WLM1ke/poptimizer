import csv
import io
import logging
import re
from collections.abc import AsyncIterator, Iterable
from datetime import date, datetime, timedelta
from typing import Final, TextIO

import aiohttp

from poptimizer import errors
from poptimizer.domain import domain
from poptimizer.domain.div import raw, status
from poptimizer.domain.moex import securities
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler

_URL: Final = "https://web.moex.com/moex-web-icdb-api/api/v1/export/register-closing-dates/csv?separator=1&language=1"
_LOOK_BACK_DAYS: Final = 14
_DATE_FMT: Final = "%m/%d/%Y %H:%M:%S"
_RE_TICKER = re.compile(r", ([A-Z]+-[A-Z]+|[A-Z]+) \[")


class DivStatusHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._lgr = logging.getLogger()
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.PortfolioUpdated) -> handler.DivStatusUpdated:
        table = await ctx.get_for_update(status.DivStatus)

        try:
            csv_file = await self._download()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError("Dividends status error") from err

        parsed_rows = self._parse(csv_file)

        sec_table = await ctx.get(securities.Securities)
        port = await ctx.get(portfolio.Portfolio)
        status_gen = _status_gen(parsed_rows, sec_table, port)

        table.update(msg.day, [row async for row in self._filter_missed(ctx, status_gen)])

        return handler.DivStatusUpdated(day=msg.day)

    async def _download(self) -> TextIO:
        async with self._http_client.get(_URL) as resp:
            if not resp.ok:
                raise errors.UseCasesError(f"bad dividends status respond {resp.reason}")

            return io.StringIO(await resp.text(encoding="cp1251"), newline="")

    def _parse(
        self,
        csv_file: TextIO,
    ) -> Iterable[tuple[domain.Ticker, date]]:
        reader = csv.reader(csv_file)
        next(reader)

        for ticker_raw, date_raw, *_ in reader:
            timestamp = datetime.strptime(date_raw, _DATE_FMT)
            day = date(timestamp.year, timestamp.month, timestamp.day)

            if day < date.today() - timedelta(days=_LOOK_BACK_DAYS):
                continue

            if (ticker_re := _RE_TICKER.search(ticker_raw)) is None:
                self._lgr.warning("Can't parse ticker from %s", ticker_raw)

                continue

            yield domain.Ticker(ticker_re[1]), day

    async def _filter_missed(self, ctx: handler.Ctx, rows: Iterable[status.Row]) -> AsyncIterator[status.Row]:
        for row in rows:
            table = await ctx.get(raw.DivRaw, domain.UID(row.ticker))

            if not table.has_day(row.day):
                self._lgr.warning("%s missed dividend at %s", row.ticker, row.day)

                yield row


def _status_gen(
    raw_rows: Iterable[tuple[domain.Ticker, date]],
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
