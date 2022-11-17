"""Создание DataLoaders."""
import asyncio
import logging
from datetime import datetime

import pandas as pd
from pydantic import BaseModel

from poptimizer.core import consts
from poptimizer.data.adapter import MarketData
from poptimizer.dl import data_loader


class FeaturesDesc(BaseModel):
    """Описание признаков модели."""

    close: bool
    div: bool
    ret: bool


class Builder:
    """Создает загрузчики данных для тренировки, тестирования и предсказания."""

    def __init__(
        self,
        data_adapter: MarketData,
    ) -> None:
        self._logger = logging.getLogger("Builder")
        self._data_adapter = data_adapter

    async def get_train_test_data_loaders(
        self,
        end: datetime,
        tickers: tuple[str, ...],
        days: data_loader.DataDays,
        feat_desc: FeaturesDesc,
        batch_size: int,
    ) -> tuple[data_loader.DataLoader, data_loader.DataLoader]:
        """Формирует загрузчики данных для тренировки и тестирования модели."""
        prices = await self._data_adapter.price(end, tickers)

        aws = [
            self._prepare_features(
                ticker,
                days,
                feat_desc,
                prices[ticker].dropna(),
            )
            for ticker in tickers
        ]

        datasets = await asyncio.gather(*aws)

        return data_loader.train(datasets, batch_size), data_loader.test(datasets)

    async def _prepare_features(
        self,
        ticker: str,
        days: data_loader.DataDays,
        feat_desc: FeaturesDesc,
        price: pd.Series,
    ) -> data_loader.OneTickerData:
        price_prev = price.shift(1).iloc[1:]
        price = price.iloc[1:]

        df_div = await self._prepare_div(ticker, price.index)

        ret_total = (price + df_div).div(price_prev).sub(1).to_list()

        features = []

        if feat_desc.ret:
            features.append(ret_total)

        if feat_desc.close:
            features.append(price.div(price_prev).sub(1))

        if feat_desc.div:
            features.append(df_div.div(price_prev))

        return data_loader.OneTickerData(
            days,
            ret_total,
            features,
        )

    async def _prepare_div(self, ticker: str, index: pd.DatetimeIndex) -> pd.Series:
        first_day = index[1]
        last_day = index[-1] + 2 * pd.tseries.offsets.BDay()

        div_df = pd.Series(0, index=index)

        async for date, div in self._data_adapter.dividends(ticker):
            if date < first_day or date >= last_day:
                continue

            div_df.iat[_ex_div_date(index, date)] += div * consts.AFTER_TAX

        return div_df


def _ex_div_date(index: pd.Index, date: datetime) -> int:
    return int(index.get_indexer([date], method="ffill")[0]) - 1
