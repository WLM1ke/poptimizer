from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pydantic import BaseModel

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.dl import datasets, features

if TYPE_CHECKING:
    from poptimizer.use_cases import handler


class NumFeatures(BaseModel):
    open: bool
    close: bool
    high: bool
    low: bool
    dividends: bool
    returns: bool
    turnover: bool
    mcftrr: bool
    meogtrr: bool
    imoex: bool
    rvi: bool


class EmbFeatures(BaseModel):
    ticker: bool


class Batch(BaseModel):
    size: int
    num_feats: NumFeatures
    emb_feats: EmbFeatures
    history_days: int

    @property
    def num_feat_count(self) -> int:
        return sum(on for _, on in self.num_feats)


class Builder:
    def __init__(self) -> None:
        self._day = consts.START_DAY
        self._tickers: tuple[domain.Ticker, ...] = ()
        self._cache: list[features.Features] = []
        self._embedding_sizes: dict[features.EmbFeat, int] = {}

    async def build(
        self,
        ctx: handler.Ctx,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
        days: datasets.Days,
        batch: Batch,
    ) -> tuple[list[datasets.TickerData], list[int]]:
        await self._update_cache(ctx, day, tickers)

        emb_feat_selected = sorted(features.EmbFeat(feat) for feat, on in batch.emb_feats if on)

        return [
            datasets.TickerData(
                days,
                feat.numerical,
                sorted(features.NumFeat(feat) for feat, on in batch.num_feats if on),
                [feat.embedding[selected].value for selected in emb_feat_selected],
            )
            for feat in self._cache
        ], [self._embedding_sizes[feat] for feat in emb_feat_selected]

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

        first_embedding = self._cache[0].embedding
        self._embedding_sizes = {feat: desc.size for feat, desc in first_embedding.items()}
        for n in range(1, len(self._cache)):
            embedding = self._cache[n].embedding
            if {feat: desc.size for feat, desc in embedding.items()} != self._embedding_sizes:
                raise errors.UseCasesError("unequal embeddings sizes")
