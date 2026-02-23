import csv
import io
import re
from collections.abc import AsyncIterable, Iterable
from datetime import date, datetime, timedelta
from typing import Final, TextIO

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer.adapters import http
from poptimizer.core import domain, errors
from poptimizer.data.moex import index, quotes, securities, usd

_ETF_URL: Final = "https://rusetfs.com/api/v1/screener"

_SECURITIES_COLUMNS: Final = (
    "SECID",
    "LOTSIZE",
    "ISIN",
    "BOARDID",
    "SECTYPE",
    "INSTRID",
)

_STATUS_URL: Final = (
    "https://web.moex.com/moex-web-icdb-api/api/v1/export/register-closing-dates/csv?separator=1&language=1"
)
_STATUS_LOOK_BACK_DAYS: Final = 14
_STATUS_DATE_FMT: Final = "%m/%d/%Y %H:%M:%S"
_STATUS_RE_TICKER: Final = re.compile(r",\s([A-Z]|[A-Z]{4}|[A-Z]{4}P|[A-Z][0-9])\s\[")


class Client:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def get_index(
        self,
        ticker: domain.Ticker,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[index.Row]:
        async with http.wrap_err(f"can't download {index} data"):
            json = await aiomoex.get_market_candles(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(end_day),
                interval=24,
                security=ticker,
                market="index",
                engine="stock",
            )

            return _deduplicate_rows(TypeAdapter(list[index.Row]).validate_python(json))

    async def get_usd(
        self,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[usd.Row]:
        async with http.wrap_err("can't download usd data"):
            json = await aiomoex.get_market_candles(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(end_day),
                interval=24,
                security="USD000UTSTOM",
                market="selt",
                engine="currency",
            )

            return TypeAdapter(list[usd.Row]).validate_python(json)

    async def get_securities(self, market: str, board: str) -> list[securities.Row]:
        async with http.wrap_err(f"can't download {market} {board} data"):
            json = await aiomoex.get_board_securities(
                self._http_client,
                market=market,
                board=board,
                columns=_SECURITIES_COLUMNS,
            )

            return TypeAdapter(list[securities.Row]).validate_python(json)

    async def get_index_tickers(self, index: securities.SectorIndex) -> list[securities.SectorIndexRow]:
        async with http.wrap_err(f"can't download index {index} data"):
            json = await aiomoex.get_index_tickers(
                self._http_client,
                index,
            )

            return TypeAdapter(list[securities.SectorIndexRow]).validate_python(json)

    async def get_etf_desc(self) -> list[securities.ETFRow]:
        async with (
            http.wrap_err("can't download etf data"),
            await self._http_client.get(_ETF_URL) as resp,
        ):
            if not resp.ok:
                raise errors.AdapterError(f"bad response from {_ETF_URL}: {resp.reason}")

            return TypeAdapter(list[securities.ETFRow]).validate_python(await resp.json())

    async def get_quotes(
        self,
        ticker: domain.Ticker,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[quotes.Row]:
        async with http.wrap_err(f"can't download {ticker} data"):
            json = await aiomoex.get_market_candles(
                session=self._http_client,
                start=start_day and str(start_day),
                end=str(end_day),
                interval=24,
                security=ticker,
                market="shares",
                engine="stock",
            )

            return TypeAdapter(list[quotes.Row]).validate_python(json)

    async def get_status(self) -> AsyncIterable[tuple[domain.Ticker, domain.Day | None]]:
        async with (
            http.wrap_err("can't download dividend status"),
            self._http_client.get(_STATUS_URL) as resp,
        ):
            if not resp.ok:
                raise errors.AdapterError(f"bad dividends status respond {resp.reason}")

            csv_file = io.StringIO(await resp.text(encoding="cp1251"), newline="")

            for row in self._prepare_status(csv_file):
                yield row

    def _prepare_status(self, csv_file: TextIO) -> Iterable[tuple[domain.Ticker, domain.Day | None]]:
        reader = csv.reader(csv_file)
        next(reader)

        for ticker_raw, date_raw, *_ in reader:
            timestamp = datetime.strptime(date_raw, _STATUS_DATE_FMT)
            day = date(timestamp.year, timestamp.month, timestamp.day)

            if day < date.today() - timedelta(days=_STATUS_LOOK_BACK_DAYS):
                continue

            match _STATUS_RE_TICKER.search(ticker_raw):
                case None:
                    yield domain.Ticker(ticker_raw), None
                case match_re:
                    yield domain.Ticker(match_re[1]), day


def _deduplicate_rows(rows: list[index.Row]) -> list[index.Row]:
    prev_row: index.Row | None = None
    rows_deduplicated: list[index.Row] = []

    for row in rows:
        if row == prev_row:
            continue

        rows_deduplicated.append(row)
        prev_row = row

    return rows_deduplicated
