import logging
import zoneinfo
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Final

import aiomoex
import psutil
from pydantic import BaseModel, Field

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.moex import index, trading_day
from poptimizer.use_cases import handler

if TYPE_CHECKING:
    import aiohttp

_MEMORY_PERCENTAGE_THRESHOLD: Final = 75

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 01.00
_END_HOUR: Final = 1
_END_MINUTE: Final = 0

_DAY_CANDLE_INTERVAL: Final = 24


class _Row(domain.Row):
    day: datetime = Field(alias="end")
    interval: int = Field(alias="interval")


class _Payload(BaseModel):
    df: list[_Row]

    def last_day(self) -> domain.Day:
        for row in self.df:
            if row.interval == _DAY_CANDLE_INTERVAL:
                return row.day.date()

        raise ValueError("no day candles data")


class DataHandler:
    def __init__(self, http_client: aiohttp.ClientSession, stop_fn: Callable[[], bool] | None) -> None:
        self._lgr = logging.getLogger()
        self._http_client = http_client
        self._stop_fn = stop_fn

    async def __call__(
        self,
        ctx: handler.Ctx,
        msg: handler.AppStarted | handler.SecFeatUpdated | handler.ForecastsAnalyzed,
    ) -> None:
        if self._stop_fn:
            match (usage := psutil.virtual_memory().percent) > _MEMORY_PERCENTAGE_THRESHOLD:
                case True:
                    self._lgr.info("Stopping due to high memory usage - %.2f%%", usage)
                    self._stop_fn()
                case False:
                    self._lgr.info("Memory usage - %.2f%%", usage)

        match msg:
            case handler.AppStarted() | handler.ForecastsAnalyzed():
                ctx.publish(await self._check(ctx))
            case handler.SecFeatUpdated():
                ctx.publish(await self._update(ctx, msg.day))

    async def _check(self, ctx: handler.Ctx) -> handler.NewDataPublished | handler.DataChecked:
        table = await ctx.get(trading_day.TradingDay)
        current_poptimizer_ver = table.poptimizer_ver == consts.__version__

        new_last_check = _last_day()
        if current_poptimizer_ver and table.last_check >= new_last_check:
            return handler.DataChecked(day=table.day)

        last_day = min(new_last_check, await self._get_last_trading_day_from_moex())

        if current_poptimizer_ver and table.day >= last_day:
            table = await ctx.get_for_update(trading_day.TradingDay)
            table.last_check = new_last_check

            return handler.DataChecked(day=table.day)

        if not current_poptimizer_ver:
            self._lgr.warning("POptimizer version updated to %s - rebuilding data", consts.__version__)

        return handler.NewDataPublished(day=last_day)

    async def _get_last_trading_day_from_moex(self) -> domain.Day:
        async with handler.wrap_http_err("trading day MOEX ISS error"):
            json = await aiomoex.get_market_candle_borders(
                self._http_client,
                security=index.IMOEX2,
                market="index",
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
