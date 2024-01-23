from datetime import date

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, field_validator

from poptimizer.core import domain
from poptimizer.data import data, day_started


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


class TradingDay(domain.Entity):
    ...


class TradingDayEnded(domain.Event):
    day: domain.Day


class TradingDayEventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def handle(self, ctx: domain.Ctx, event: day_started.DayStarted) -> None:
        table = await ctx.get(TradingDay)

        if table.day >= event.day:
            return

        json = await aiomoex.get_board_dates(
            self._http_client,
            board="TQBR",
            market="shares",
            engine="stock",
        )

        payload = _Payload.model_validate({"df": json})
        new_last_day = payload.last_day()

        if table.day < new_last_day:
            table.day = new_last_day
            ctx.publish(TradingDayEnded(day=new_last_day))
