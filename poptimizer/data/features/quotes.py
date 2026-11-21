import asyncio
from datetime import datetime
from typing import Final, cast

import numpy as np
import pandas as pd

from poptimizer.core import consts, domain, fsm
from poptimizer.data.div import processed
from poptimizer.data.features.features import Features, NumFeat
from poptimizer.data.moex import quotes
from poptimizer.portfolio.models import portfolio

_T_PLUS_1_START: Final = datetime(2023, 7, 31)


async def update(ctx: fsm.Ctx, trading_days: list[domain.Day]) -> None:
    async with asyncio.TaskGroup() as tg:
        port_task = tg.create_task(ctx.get(portfolio.Portfolio))

        index = pd.DatetimeIndex(trading_days)

        for pos in (await port_task).positions:
            tg.create_task(_build_features(ctx, domain.UID(pos.ticker), index))


async def _build_features(ctx: fsm.Ctx, ticker: domain.UID, index: pd.DatetimeIndex) -> None:
    quotes_table = await ctx.get(quotes.Quotes, ticker)

    first_day = pd.Timestamp(quotes_table.df[0].day)
    quotes_df = (
        pd.DataFrame([row.model_dump() for row in quotes_table.df]).set_index("day").reindex(index).loc[first_day:]
    )
    quotes_df.columns = [NumFeat(col) for col in quotes_df.columns]

    turnover_df = np.log1p(quotes_df[NumFeat.TURNOVER].fillna(0).iloc[1:])

    quotes_df[NumFeat.CLOSE] = quotes_df[NumFeat.CLOSE].ffill()
    quotes_df = quotes_df[[NumFeat.CLOSE, NumFeat.OPEN, NumFeat.HIGH, NumFeat.LOW]].ffill(axis=1)
    close_prev = quotes_df[NumFeat.CLOSE].shift(1).iloc[1:]
    quotes_df = quotes_df.iloc[1:]

    dividends = await _prepare_div(ctx, quotes_table.uid, pd.DatetimeIndex(quotes_df.index))
    quotes_df[NumFeat.DIVIDENDS] = dividends + close_prev
    quotes_df[NumFeat.RETURNS] = dividends + quotes_df[NumFeat.CLOSE]
    quotes_df = pd.DataFrame(
        np.log(quotes_df.div(close_prev, axis="index")),
        index=quotes_df.index,
        columns=quotes_df.columns,
    )
    quotes_df[NumFeat.TURNOVER] = turnover_df

    feat = await ctx.get_for_update(Features, quotes_table.uid)
    feat.update_numerical(quotes_df)


async def _prepare_div(ctx: fsm.Ctx, ticker: domain.UID, index: pd.DatetimeIndex) -> pd.Series[float]:
    div_table = await ctx.get(processed.Dividends, ticker)

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

    return cast("int", index.get_indexer(pd.DatetimeIndex([date]), method="ffill")[0]) - (shift - 1)
