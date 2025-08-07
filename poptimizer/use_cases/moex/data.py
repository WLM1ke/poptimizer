import logging
import zoneinfo
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Final

import aiohttp
import aiomoex
import psutil
from pydantic import BaseModel, Field, field_validator

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.moex import trading_day
from poptimizer.use_cases import handler

_MEMORY_PERCENTAGE_THRESHOLD: Final = 75

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 01.00
_END_HOUR: Final = 1
_END_MINUTE: Final = 0


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


class DataHandler:
    def __init__(self, http_client: aiohttp.ClientSession, stop_fn: Callable[[], bool] | None) -> None:
        self._lgr = logging.getLogger()
        self._http_client = http_client
        self._stop_fn = stop_fn

    async def __call__(
        self,
        ctx: handler.Ctx,
        msg: handler.AppStarted | handler.SecFeatUpdated | handler.ForecastsAnalyzed,
    ) -> handler.NewDataPublished | handler.DataChecked | None:
        if self._stop_fn:
            match (usage := psutil.virtual_memory().percent) > _MEMORY_PERCENTAGE_THRESHOLD:
                case True:
                    self._lgr.info("Stopping due to high memory usage - %.2f%%", usage)
                    self._stop_fn()
                case False:
                    self._lgr.info("Memory usage - %.2f%%", usage)

        match msg:
            case handler.AppStarted() | handler.ForecastsAnalyzed():
                return await self._check(ctx)
            case handler.SecFeatUpdated():
                return await self._update(ctx, msg.day)

    async def _check(self, ctx: handler.Ctx) -> handler.NewDataPublished | handler.DataChecked:
        table = await ctx.get(trading_day.TradingDay)
        current_poptimizer_ver = table.poptimizer_ver == consts.__version__

        new_last_check = _last_day()
        if current_poptimizer_ver and table.last_check >= new_last_check:
            return handler.DataChecked(day=table.day)

        last_day = await self._get_last_trading_day_from_moex()

        if current_poptimizer_ver and table.day >= last_day:
            table = await ctx.get_for_update(trading_day.TradingDay)
            table.last_check = new_last_check

            return handler.DataChecked(day=table.day)

        if not current_poptimizer_ver:
            self._lgr.warning("POptimizer version updated to %s - rebuilding data", consts.__version__)

        return handler.NewDataPublished(day=last_day)

    async def _get_last_trading_day_from_moex(self) -> domain.Day:
        async with handler.wrap_http_err("trading day MOEX ISS error"):
            json = await aiomoex.get_board_dates(
                self._http_client,
                board="TQBR",
                market="shares",
                engine="stock",
            )

        with handler.wrap_validation_err("invalid trading day data"):
            return _Payload.model_validate({"df": json}).last_day()

    async def _update(self, ctx: handler.Ctx, last_trading_day: domain.Day) -> handler.DataChecked:
        table = await ctx.get_for_update(trading_day.TradingDay)
        table.update_last_trading_day(last_trading_day, consts.__version__)
        self._lgr.info("Data updated for %s", last_trading_day)

        return handler.DataChecked(day=table.day)


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
