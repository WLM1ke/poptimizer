import asyncio
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from poptimizer.core import domain, fsms
from poptimizer.data.features import features
from poptimizer.data.moex import index, securities
from poptimizer.data.portfolio import portfolio

if TYPE_CHECKING:
    from pydantic import FiniteFloat


async def update(ctx: fsms.CoreCtx) -> None:
    async with asyncio.TaskGroup() as tg:
        port_task = tg.create_task(ctx.get(portfolio.Portfolio))
        sec = await ctx.get(securities.Securities)
        indexes = await _load_indexes(ctx, pd.DatetimeIndex(sec.trading_days))

        for pos in (await port_task).positions:
            tg.create_task(_add_indexes_features(ctx, domain.UID(pos.ticker), indexes))


async def _load_indexes(ctx: fsms.CoreCtx, trading_days: pd.DatetimeIndex) -> list[dict[features.NumFeat, FiniteFloat]]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(ctx.get(index.Index, domain.UID(uid))) for uid in index.INDEXES]

    indexes: list[pd.DataFrame] = []

    for task in tasks:
        index_table = await task
        index_df = pd.DataFrame(index_table.model_dump()["df"]).set_index("day")
        combined_index = index_df.index.union(trading_days, sort=True)
        index_df = index_df.reindex(combined_index).ffill().loc[trading_days]

        match index_table.uid:
            case index.RVI:
                index_df = index_df / 100
            case _:
                index_df: pd.DataFrame = np.log1p(index_df.pct_change())  # type: ignore[reportUnknownMemberType]

        indexes.append(index_df)

    return [
        {features.NumFeat(uid.lower()): indexes[col].iloc[row, 0] for col, uid in enumerate(index.INDEXES)}  # type: ignore[reportUnknownMemberType]
        for row in range(1, len(trading_days))
    ]


async def _add_indexes_features(
    ctx: fsms.CoreCtx,
    ticker: domain.UID,
    indexes: list[dict[features.NumFeat, FiniteFloat]],
) -> None:
    features_table = await ctx.get_for_update(features.Features, ticker)

    delta_len = len(indexes) - len(features_table.numerical)

    for n in range(len(features_table.numerical)):
        features_table.numerical[n] |= indexes[n + delta_len]
