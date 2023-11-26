"""Информация о торговых днях."""
from datetime import date

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, field_validator

from poptimizer.core import domain
from poptimizer.data import data, day_started


class _TradingDate(data.Row):
    day: domain.Day = Field(alias="till")


class _Payload(BaseModel):
    df: list[_TradingDate]

    def last_day(self) -> date:
        return self.df[0].day

    @field_validator("df")
    def _must_be_one_row(cls, df: list[_TradingDate]) -> list[_TradingDate]:
        if (count := len(df)) != 1:
            raise ValueError(f"wrong rows count {count}")

        return df


class TradingDay(domain.Entity):
    ...


class TradingDayEnded(domain.Event):
    day: domain.Day


class EventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def handle(self, ctx: domain.Ctx, event: day_started.DayStarted) -> None:  # noqa: ARG002
        table = await ctx.get(TradingDay)

        json = await aiomoex.get_board_dates(
            self._http_client,
            board="TQBR",
            market="shares",
            engine="stock",
        )

        payload = _Payload.model_validate({"df": json})
        new_last_day = payload.last_day()

        if table.timestamp < new_last_day:
            table.timestamp = new_last_day
            ctx.publish(TradingDayEnded(day=new_last_day))
