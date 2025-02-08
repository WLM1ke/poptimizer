import logging
import zoneinfo
from datetime import date, datetime, timedelta
from typing import Final

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, field_validator

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.moex import trading_day
from poptimizer.use_cases import handler

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


class DataHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._lgr = logging.getLogger()
        self._http_client = http_client

    async def __call__(
        self,
        ctx: handler.Ctx,
        msg: handler.AppStarted | handler.IndexFeatUpdated | handler.ForecastsAnalyzed,
    ) -> handler.NewDataPublished | handler.DataChecked:
        match msg:
            case handler.AppStarted() | handler.ForecastsAnalyzed():
                return await self._check(ctx)
            case handler.IndexFeatUpdated():
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
        try:
            json = await aiomoex.get_board_dates(
                self._http_client,
                board="TQBR",
                market="shares",
                engine="stock",
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise errors.UseCasesError("trading day MOEX ISS error") from err

        try:
            payload = _Payload.model_validate({"df": json})
        except ValueError as err:
            raise errors.UseCasesError("invalid trading day data") from err

        return payload.last_day()

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
