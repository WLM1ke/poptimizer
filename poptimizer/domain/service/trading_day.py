import zoneinfo
from datetime import date, datetime, timedelta
from typing import Final

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, field_validator

from poptimizer.domain import consts
from poptimizer.domain.entity import entity, trading_day
from poptimizer.domain.service import service

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45


class _Row(entity.Row):
    day: entity.Day = Field(alias="till")


class _Payload(BaseModel):
    df: list[_Row]

    def last_day(self) -> date:
        return self.df[0].day

    @field_validator("df")
    def _must_be_one_row(cls, df: list[_Row]) -> list[_Row]:
        if (count := len(df)) != 1:
            raise ValueError(f"wrong rows count {count}")

        return df


class TradingDayService:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client
        self._last_check = consts.START_DAY

    async def is_update_required(self, ctx: service.Ctx) -> entity.Day | None:
        await self._maybe_init(ctx)

        new_last_check = _last_day()
        if self._last_check >= new_last_check:
            ctx.info("Data update not required")
            return None

        json = await aiomoex.get_board_dates(
            self._http_client,
            board="TQBR",
            market="shares",
            engine="stock",
        )
        payload = _Payload.model_validate({"df": json})
        new_last_day = payload.last_day()

        if new_last_day > self._last_check:
            ctx.info(f"New data for {new_last_day}")
            self._last_check = new_last_day

            return new_last_day

        ctx.info(f"No new data for {new_last_check}")
        table = await ctx.get_for_update(trading_day.Table)
        table.day = new_last_check
        self._last_check = new_last_check

        return None

    async def _maybe_init(self, ctx: service.Ctx) -> None:
        if self._last_check != consts.START_DAY:
            return

        table = await ctx.get_for_update(trading_day.Table)
        self._last_check = table.day
        ctx.info(f"Last data - {table.last}")
        ctx.info(f"Last check - {table.day}")


class TradingDayUpdater:
    async def __call__(self, ctx: service.Ctx, update_day: entity.Day) -> None:
        table = await ctx.get_for_update(trading_day.Table)
        table.day = update_day
        table.last = update_day


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
