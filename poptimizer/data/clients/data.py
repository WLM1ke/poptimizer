import io
import logging
from collections.abc import Iterable
from typing import Final

import aiohttp
import aiomoex
from lxml import html
from pydantic import TypeAdapter

from poptimizer.adapters import http
from poptimizer.core import domain, errors
from poptimizer.data.clients.cpi import cpi_parser
from poptimizer.data.clients.reestry import div_parser
from poptimizer.data.clients.status import status_parser
from poptimizer.data.cpi import cpi
from poptimizer.data.div import raw, status
from poptimizer.data.moex import index, quotes, securities

_SECURITIES_COLUMNS: Final = (
    "SECID",
    "LOTSIZE",
    "ISIN",
    "BOARDID",
    "SECTYPE",
    "INSTRID",
)
_ETF_URL: Final = "https://rusetfs.com/api/v1/screener"
_STATUS_URL: Final = (
    "https://web.moex.com/moex-web-icdb-api/api/v1/export/register-closing-dates/csv?separator=1&language=1"
)
_CBR_URL: Final = "https://www.cbr.ru/Content/Document/File/108632/indicators_cpd.xlsx"
_REESTRY_URL: Final = "https://закрытияреестров.рф/_/"


class Client:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client
        self._lgr = logging.getLogger("DataClient")

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

    async def get_status(self) -> Iterable[tuple[domain.Ticker, domain.Day]]:
        async with (
            http.wrap_err("can't download dividend status"),
            self._http_client.get(_STATUS_URL) as resp,
        ):
            if not resp.ok:
                raise errors.AdapterError(f"bad dividends status respond {resp.reason}")

            csv_file = io.StringIO(await resp.text(encoding="cp1251"), newline="")

            return status_parser(self._lgr, csv_file)

    async def get_cpi(self) -> list[cpi.Row]:
        async with (
            http.wrap_err("can't download CPI data"),
            self._http_client.get(_CBR_URL) as resp,
        ):
            if not resp.ok:
                raise errors.AdapterError(f"bad CPI respond status {resp.reason}")

            return cpi_parser(io.BytesIO(await resp.read()))

    async def get_divs(self, start_day: domain.Day, row: status.Row) -> list[raw.Row]:
        async with http.wrap_err(f"can't load dividends for {row.ticker}"):
            url = await self._find_div_url(row.ticker_base)
            html_page = await self._load_div_html(url, row.ticker)

        return div_parser(self._lgr, html_page, 1 + row.preferred, start_day)

    async def _find_div_url(self, ticker_base: str) -> str:
        async with self._http_client.get(_REESTRY_URL) as resp:
            if not resp.ok:
                raise errors.AdapterError(f"bad respond status {resp.reason}")

            html_page = await resp.text()

        links: list[html.HtmlElement] = html.document_fromstring(html_page).xpath("//*/a")  # type: ignore[reportUnknownMemberType]

        for link in links:
            link_text = link.text_content()
            if ticker_base in link_text or ticker_base.lower() in link_text:
                return _REESTRY_URL + link.attrib["href"]

        raise errors.AdapterError(f"{ticker_base} dividends not found")

    async def _load_div_html(self, url: str, ticker: domain.Ticker) -> str:
        async with self._http_client.get(url) as resp:
            if not resp.ok:
                raise errors.AdapterError(f"{ticker} bad respond status {resp.reason}")

            return await resp.text()


def _deduplicate_rows(rows: list[index.Row]) -> list[index.Row]:
    prev_row: index.Row | None = None
    rows_deduplicated: list[index.Row] = []

    for row in rows:
        if row == prev_row:
            continue

        rows_deduplicated.append(row)
        prev_row = row

    return rows_deduplicated
