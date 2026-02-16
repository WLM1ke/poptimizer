from datetime import datetime
from typing import Final

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, TypeAdapter

from poptimizer.actors.data.moex.models import securities
from poptimizer.adapters.http import wrap_err
from poptimizer.core import domain, errors
from poptimizer.domain.moex import index

_ETF_URL: Final = "https://rusetfs.com/api/v1/screener"

_DAY_CANDLE_INTERVAL: Final = 24

_SECURITIES_COLUMNS: Final = (
    "SECID",
    "LOTSIZE",
    "ISIN",
    "BOARDID",
    "SECTYPE",
    "INSTRID",
)


class _CandleBordersRow(domain.Row):
    day: datetime = Field(alias="end")
    interval: int = Field(alias="interval")


class _CandleBorders(BaseModel):
    df: list[_CandleBordersRow]

    def last_day(self) -> domain.Day:
        for row in self.df:
            if row.interval == _DAY_CANDLE_INTERVAL:
                return row.day.date()

        raise errors.AdapterError("no day candles data")


class Client:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def last_trading_day(self) -> domain.Day:
        async with wrap_err("trading day MOEX ISS error"):
            json = await aiomoex.get_market_candle_borders(
                self._http_client,
                security=index.IMOEX2,
                market="index",
            )

            return _CandleBorders.model_validate({"df": json}).last_day()

    async def get_board_securities(self, market: str, board: str) -> list[securities.Security]:
        async with wrap_err(f"can't download {market} {board} data"):
            raw_data = await aiomoex.get_board_securities(
                self._http_client,
                market=market,
                board=board,
                columns=_SECURITIES_COLUMNS,
            )

            return TypeAdapter(list[securities.Security]).validate_python(raw_data)

    async def get_index_tickers(self, index: securities.SectorIndex) -> list[securities.SectorIndexRow]:
        async with wrap_err(f"can't download index {index} data"):
            raw_data = await aiomoex.get_index_tickers(
                self._http_client,
                index,
            )

            return TypeAdapter(list[securities.SectorIndexRow]).validate_python(raw_data)

    async def get_etf_desc(self) -> list[securities.ETFRow]:
        async with wrap_err("can't download etf data"):
            json = await self._http_client.get(_ETF_URL)
            if not json.ok:
                raise errors.AdapterError(f"bad response from {_ETF_URL}: {json.reason}")

            return TypeAdapter(list[securities.ETFRow]).validate_python(await json.json())
