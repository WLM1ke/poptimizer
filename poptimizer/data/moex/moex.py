from typing import Final

import aiohttp
import aiomoex
from pydantic import TypeAdapter

from poptimizer.adapters.http import wrap_err
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


class Client:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def get_index(
        self,
        ticker: domain.Ticker,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[index.Row]:
        async with wrap_err(f"can't download {index} data"):
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
        async with wrap_err("can't download usd data"):
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
        async with wrap_err(f"can't download {market} {board} data"):
            json = await aiomoex.get_board_securities(
                self._http_client,
                market=market,
                board=board,
                columns=_SECURITIES_COLUMNS,
            )

            return TypeAdapter(list[securities.Row]).validate_python(json)

    async def get_index_tickers(self, index: securities.SectorIndex) -> list[securities.SectorIndexRow]:
        async with wrap_err(f"can't download index {index} data"):
            json = await aiomoex.get_index_tickers(
                self._http_client,
                index,
            )

            return TypeAdapter(list[securities.SectorIndexRow]).validate_python(json)

    async def get_etf_desc(self) -> list[securities.ETFRow]:
        async with wrap_err("can't download etf data"):
            json = await self._http_client.get(_ETF_URL)
            if not json.ok:
                raise errors.AdapterError(f"bad response from {_ETF_URL}: {json.reason}")

            return TypeAdapter(list[securities.ETFRow]).validate_python(await json.json())

    async def get_quotes(
        self,
        ticker: domain.Ticker,
        start_day: domain.Day | None,
        end_day: domain.Day,
    ) -> list[quotes.Row]:
        async with wrap_err(f"can't download {ticker} data"):
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


def _deduplicate_rows(rows: list[index.Row]) -> list[index.Row]:
    prev_row: index.Row | None = None
    rows_deduplicated: list[index.Row] = []

    for row in rows:
        if row == prev_row:
            continue

        rows_deduplicated.append(row)
        prev_row = row

    return rows_deduplicated
