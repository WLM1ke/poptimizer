import logging
import zoneinfo
from datetime import date, datetime, timedelta
from typing import Final

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, field_validator

from poptimizer import errors
from poptimizer.domain import domain
from poptimizer.domain.data import trading_day
from poptimizer.handlers import handler

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45


class _Row(domain.Row):
    day: domain.Day = Field(alias="till")


class _Payload(BaseModel):
    df: list[_Row]

    def last_day(self) -> domain.Day:
        return self.df[0].day

    @field_validator("df")
    def _must_be_one_row(cls, df: list[_Row]) -> list[_Row]:
        if (count := len(df)) != 1:
            raise ValueError(f"wrong rows count {count}")

        return df


class TradingDayHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._lgr = logging.getLogger()
        self._http_client = http_client

    async def check(self, ctx: handler.Ctx, msg: handler.AppStarted | handler.EvolutionStepFinished) -> None:  # noqa: ARG002
        table = await ctx.get(trading_day.TradingDay)

        new_last_check = _last_day()
        if table.day == new_last_check:
            ctx.publish(handler.DataChecked())

            return

        last_day = await self._get_last_trading_day_from_moex()

        if table.day >= last_day:
            table = await ctx.get_for_update(trading_day.TradingDay)
            table.update_last_check(new_last_check)
            ctx.publish(handler.DataChecked())

            return

        ctx.publish(handler.DataPublished(day=last_day))

    async def _get_last_trading_day_from_moex(self) -> domain.Day:
        try:
            json = await aiomoex.get_board_dates(
                self._http_client,
                board="TQBR",
                market="shares",
                engine="stock",
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.HandlerError("MOEX IIS") from err

        try:
            payload = _Payload.model_validate({"df": json})
        except ValueError as err:
            raise errors.HandlerError("invalid trading day data") from err

        return payload.last_day()

    async def update(self, ctx: handler.Ctx, msg: handler.DataPublished) -> None:
        table = await ctx.get_for_update(trading_day.TradingDay)
        table.update_last_trading_day(msg.day)
        ctx.publish(handler.DataUpdated(day=msg.day))


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
