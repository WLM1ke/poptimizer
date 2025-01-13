from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pydantic import BaseModel

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.dl import datasets, features

if TYPE_CHECKING:
    from poptimizer.use_cases import handler


class Features(BaseModel):
    open: bool
    close: bool
    high: bool
    low: bool
    dividends: bool
    returns: bool
    turnover: bool


class Builder:
    def __init__(self) -> None:
        self._day = consts.START_DAY
        self._tickers: tuple[domain.Ticker, ...] = ()
        self._cache: list[features.Features] = []

    async def build(
        self,
        ctx: handler.Ctx,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
        feats: Features,
        days: datasets.Days,
    ) -> list[datasets.TickerData]:
        await self._update_cache(ctx, day, tickers)

        num_feat = {features.NumFeat(feat) for feat, on in feats if on}

        return [
            datasets.TickerData(
                feat.numerical,
                days,
                num_feat,
            )
            for feat in self._cache
        ]

    async def _update_cache(
        self,
        ctx: handler.Ctx,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
    ) -> None:
        if self._day == day and self._tickers == tickers:
            return

        self._day = day
        self._tickers = tickers

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(ctx.get(features.Features, domain.UID(ticker))) for ticker in tickers]

        self._cache = [await task for task in tasks]
