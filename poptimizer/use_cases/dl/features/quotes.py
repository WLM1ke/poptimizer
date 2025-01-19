from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Final

import numpy as np
import pandas as pd

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.div import div
from poptimizer.domain.dl.features import Features, NumFeat
from poptimizer.domain.moex import quotes
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler

_T_PLUS_1_START: Final = datetime(2023, 7, 31)


class QuotesFeatHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.PortfolioUpdated) -> handler.QuotesFeatUpdated:
        index = pd.DatetimeIndex(msg.trading_days)
        port = await ctx.get(portfolio.Portfolio)

        async with asyncio.TaskGroup() as tg:
            for pos in port.positions:
                tg.create_task(_build_features(ctx, domain.UID(pos.ticker), index))

        return handler.QuotesFeatUpdated(trading_days=msg.trading_days)


async def _build_features(ctx: handler.Ctx, ticker: domain.UID, index: pd.DatetimeIndex) -> None:
    quotes_table = await ctx.get(quotes.Quotes, ticker)

    first_day = pd.Timestamp(quotes_table.df[0].day)
    quotes_df = pd.DataFrame(quotes_table.model_dump()["df"]).set_index("day").reindex(index).loc[first_day:]  # type: ignore[reportUnknownMemberType]
    quotes_df.columns = [NumFeat(col) for col in quotes_df.columns]

    turnover_df = np.log1p(quotes_df[NumFeat.TURNOVER].fillna(0).iloc[1:])  # type: ignore[reportUnknownMemberType]

    quotes_df[NumFeat.CLOSE] = quotes_df[NumFeat.CLOSE].ffill()  # type: ignore[reportUnknownMemberType]
    quotes_df = quotes_df[[NumFeat.CLOSE, NumFeat.OPEN, NumFeat.HIGH, NumFeat.LOW]].ffill(axis=1)  # type: ignore[reportUnknownMemberType]
    close_prev = quotes_df[NumFeat.CLOSE].shift(1).iloc[1:]  # type: ignore[reportUnknownMemberType]
    quotes_df = quotes_df.iloc[1:]

    dividends = await _prepare_div(ctx, quotes_table.uid, quotes_df.index)  # type: ignore[reportUnknownMemberType]
    quotes_df[NumFeat.DIVIDENDS] = dividends + close_prev
    quotes_df[NumFeat.RETURNS] = dividends + quotes_df[NumFeat.CLOSE]
    quotes_df = np.log(quotes_df.div(close_prev, axis="index"))  # type: ignore[reportUnknownMemberType]
    quotes_df[NumFeat.TURNOVER] = turnover_df  # type: ignore[reportUnknownMemberType]

    feat = await ctx.get_for_update(Features, quotes_table.uid)
    feat.update(quotes_table.day, quotes_df)  # type: ignore[reportUnknownMemberType]


async def _prepare_div(ctx: handler.Ctx, ticker: domain.UID, index: pd.DatetimeIndex) -> pd.Series[float]:
    div_table = await ctx.get(div.Dividends, ticker)

    first_day = index[1]
    last_day = index[-1] + 2 * pd.tseries.offsets.BDay()

    div_df = pd.Series(0, index=index, dtype=float, name=NumFeat.DIVIDENDS)

    for row in div_table.df:
        timestamp = pd.Timestamp(row.day)
        if timestamp < first_day or timestamp >= last_day:
            continue

        div_df.iloc[_ex_div_date(index, timestamp)] += row.dividend * consts.AFTER_TAX

    return div_df


def _ex_div_date(index: pd.DatetimeIndex, date: datetime) -> int:
    shift = 2
    if date > _T_PLUS_1_START:
        shift = 1

    return index.get_indexer([date], method="ffill")[0] - (shift - 1)  # type: ignore[reportUnknownArgumentType]
