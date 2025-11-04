import asyncio
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from poptimizer.domain import domain
from poptimizer.domain.dl import features
from poptimizer.domain.moex import index
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler

if TYPE_CHECKING:
    from pydantic import FiniteFloat


class IndexesFeatHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.QuotesFeatUpdated) -> None:
        indexes = await _load_indexes(ctx, pd.DatetimeIndex(msg.trading_days))
        port = await ctx.get(portfolio.Portfolio)

        async with asyncio.TaskGroup() as tg:
            for pos in port.positions:
                tg.create_task(_add_indexes_features(ctx, domain.UID(pos.ticker), indexes))

        ctx.publish(handler.IndexFeatUpdated(trading_days=msg.trading_days))


async def _load_indexes(ctx: handler.Ctx, df_index: pd.DatetimeIndex) -> list[dict[features.NumFeat, FiniteFloat]]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(ctx.get(index.Index, uid)) for uid in index.INDEXES]

    indexes: list[pd.DataFrame] = []

    for task in tasks:
        index_table = await task
        index_df = pd.DataFrame(index_table.model_dump()["df"]).set_index("day")
        combined_index = index_df.index.union(df_index, sort=True)
        index_df = index_df.reindex(combined_index).ffill().loc[df_index]

        match index_table.uid:
            case index.RVI:
                index_df = index_df / 100
            case _:
                index_df: pd.DataFrame = np.log1p(index_df.pct_change())  # type: ignore[reportUnknownMemberType]

        indexes.append(index_df)

    return [
        {features.NumFeat(uid.lower()): indexes[col].iloc[row, 0] for col, uid in enumerate(index.INDEXES)}  # type: ignore[reportUnknownMemberType]
        for row in range(1, len(df_index))
    ]


async def _add_indexes_features(
    ctx: handler.Ctx, ticker: domain.UID, indexes: list[dict[features.NumFeat, FiniteFloat]]
) -> None:
    quotes_table = await ctx.get_for_update(features.Features, ticker)

    delta_len = len(indexes) - len(quotes_table.numerical)

    for n in range(len(quotes_table.numerical)):
        quotes_table.numerical[n] |= indexes[n + delta_len]
