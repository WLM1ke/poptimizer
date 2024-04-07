import zoneinfo
from datetime import date, datetime, timedelta
from typing import Final

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, field_validator

from poptimizer.core import domain
from poptimizer.data import data

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45


class _Row(data.Row):
    day: domain.Day = Field(alias="till")


class _Payload(BaseModel):
    df: list[_Row]

    def last_day(self) -> date:
        return self.df[0].day

    @field_validator("df")
    def _must_be_one_row(cls, df: list[_Row]) -> list[_Row]:
        if (count := len(df)) != 1:
            raise ValueError(f"wrong rows count {count}")

        return df


class TradingDay(domain.Entity): ...


class CheckTradingDay:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def __call__(self, ctx: domain.Ctx, state: data.LastTradingDay) -> bool:
        table = await ctx.get(TradingDay, for_update=False)

        if table.day >= _last_day():
            return False

        json = await aiomoex.get_board_dates(
            self._http_client,
            board="TQBR",
            market="shares",
            engine="stock",
        )

        payload = _Payload.model_validate({"df": json})
        state.day = payload.last_day()

        return True


class TradingDayUpdater:
    async def __call__(self, ctx: domain.Ctx, state: data.LastTradingDay) -> bool:
        table = await ctx.get(TradingDay)
        table.day = state.day

        return True


def _last_day() -> date:
    now = datetime.now(_MOEX_TZ)
    end_of_trading = now.replace(
        hour=_END_HOUR,
        minute=_END_MINUTE,
        second=0,
        microsecond=0,
        tzinfo=_MOEX_TZ,
    )

    delta = 2
    if end_of_trading < now:
        delta = 1

    return date(
        year=now.year,
        month=now.month,
        day=now.day,
    ) - timedelta(days=delta)
