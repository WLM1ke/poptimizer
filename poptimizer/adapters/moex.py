from datetime import datetime
from typing import Final

import aiohttp
import aiomoex
from pydantic import BaseModel, Field

from poptimizer.adapters.http import wrap_err
from poptimizer.core import domain, errors
from poptimizer.domain.moex import index

_DAY_CANDLE_INTERVAL: Final = 24


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
