from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Final

import pandas as pd
from pydantic import BaseModel

from poptimizer.domain import consts
from poptimizer.domain.entity.dl import datasets

if TYPE_CHECKING:
    from poptimizer.domain.service import view


_T_PLUS_1_START: Final = datetime(2023, 7, 31)


class Features(BaseModel):
    tickers: tuple[str, ...]
    last_date: datetime
    close: bool
    div: bool
    ret: bool


class Builder:
    def __init__(
        self,
        view_service: view.Service,
    ) -> None:
        self._data_adapter = view_service

    async def build(
        self,
        feats: Features,
        days: datasets.Days,
    ) -> list[datasets.OneTickerData]:
        prices = await self._data_adapter.close(feats.last_date, feats.tickers)

        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(
                    self._prepare_features(
                        ticker,
                        feats,
                        days,
                        prices[ticker].dropna(),  # type: ignore[reportUnknownMemberType]
                    )
                )
                for ticker in feats.tickers
            ]

        return [task.result() for task in tasks]

    async def _prepare_features(
        self,
        ticker: str,
        feats: Features,
        days: datasets.Days,
        price: pd.Series[float],
    ) -> datasets.OneTickerData:
        price_prev = price.shift(1).iloc[1:]  # type: ignore[reportUnknownMemberType]
        price = price.iloc[1:]  # type: ignore[reportUnknownMemberType]

        df_div = await self._prepare_div(ticker, price.index)  # type: ignore[reportUnknownMemberType]

        ret_total = (price + df_div).div(price_prev).sub(1)  # type: ignore[reportUnknownMemberType]

        features: list[pd.Series[float]] = []

        if feats.ret:
            features.append(ret_total)

        if feats.close:
            features.append(price.div(price_prev).sub(1))  # type: ignore[reportUnknownMemberType]

        if feats.div:
            features.append(df_div.div(price_prev))  # type: ignore[reportUnknownMemberType]

        return datasets.OneTickerData(
            days,
            ret_total,
            features,
        )

    async def _prepare_div(self, ticker: str, index: pd.DatetimeIndex) -> pd.Series[float]:
        first_day = index[1]
        last_day = index[-1] + 2 * pd.tseries.offsets.BDay()

        div_df = pd.Series(0, index=index, dtype=float)

        async for date, div in self._data_adapter.dividends(ticker):
            if date < first_day or date >= last_day:
                continue

            div_df.iloc[_ex_div_date(index, date)] += div * consts.AFTER_TAX

        return div_df


def _ex_div_date(index: pd.DatetimeIndex, date: datetime) -> int:
    shift = 2
    if date > _T_PLUS_1_START:
        shift = 1

    return index.get_indexer([date], method="ffill")[0] - (shift - 1)  # type: ignore[reportUnknownArgumentType]
