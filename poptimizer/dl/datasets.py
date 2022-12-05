"""Загрузчики данных."""
import asyncio
from datetime import datetime
from enum import Enum, auto, unique

import numpy as np
import pandas as pd
import torch
from pydantic import BaseModel
from torch.utils import data

from poptimizer.core import consts
from poptimizer.data.adapter import MarketData
from poptimizer.dl import exceptions


@unique
class FeatTypes(Enum):
    """Типы признаков.

    Являются ключами для словаря с отдельными обучающими примерами.
    """

    LABEL1P = auto()
    RETURNS = auto()
    NUMERICAL = auto()


Batch = dict[FeatTypes, torch.Tensor]


class Days(BaseModel):
    """Описание количества дней для тестирования, построения прогноза и истории в отдельном обучающем примере."""

    history: int
    forecast: int
    test: int


class OneTickerData(data.Dataset[dict[FeatTypes, torch.Tensor]]):
    """Данные для построения признака по одному тикеру.

    Позволяет создавать Dataset(ы) для обучения, тестирования и прогнозирования.
    """

    def __init__(
        self,
        days: Days,
        ret_total: pd.Series,
        num_feat: list[pd.Series],
    ) -> None:
        self._history_days = days.history
        self._test_days = days.test
        self._forecast_days = days.forecast

        self._all_days = len(ret_total)

        min_days_for_one_train_and_test = self._history_days + 2 * self._forecast_days + self._test_days - 1
        if self._all_days < min_days_for_one_train_and_test:
            raise exceptions.FeaturesError("too short history")

        self._ret_total = torch.tensor(
            ret_total.values,
            dtype=torch.float,
            device=consts.DEVICE,
        )

        ret = (
            pd.Series(np.log1p(ret_total))
            .rolling(self._forecast_days)
            .sum()
            .shift(-(self._forecast_days + self._history_days - 1))
            .values
        )
        self._label1p = torch.tensor(
            np.exp(ret),
            dtype=torch.float,
            device=consts.DEVICE,
        )

        if any(not ret_total.index.equals(df.index) for df in num_feat):
            raise exceptions.FeaturesError("features index missmatch")

        self._num_feat = torch.vstack(
            [
                torch.tensor(
                    feat.values,
                    dtype=torch.float,
                    device=consts.DEVICE,
                )
                for feat in num_feat
            ],
        )

    def __len__(self) -> int:
        """Количество доступных примеров."""
        return self._all_days - self._history_days + 1

    def __getitem__(self, start_day: int) -> Batch:
        """Выдает обучающий пример с заданным номером.

        Метка может отсутствовать для конца семпла.
        """
        case = {
            FeatTypes.NUMERICAL: self._num_feat[:, start_day : start_day + self._history_days],
            FeatTypes.RETURNS: self._ret_total[start_day : start_day + self._history_days],
        }

        if start_day < self._all_days - (self._history_days + self._forecast_days) + 1:
            case[FeatTypes.LABEL1P] = self._label1p[start_day].reshape(-1)

        return case

    def train_dataset(self) -> data.Subset[Batch]:
        """Dataset для обучения."""
        end = (
            self._all_days
            - (self._forecast_days + self._test_days - 1)
            - (self._history_days + self._forecast_days - 1)
        )

        return data.Subset(self, range(end))

    def test_dataset(self) -> data.Subset[Batch]:
        """Dataset для тестирования."""
        end = self._all_days - (self._history_days + self._forecast_days - 1)

        return data.Subset(self, range(end - self._test_days, end))

    def forecast_dataset(self) -> data.Subset[Batch]:
        """Dataset для построения прогноза."""
        start = self._all_days - self._history_days

        return data.Subset(self, range(start, start + 1))


class Features(BaseModel):
    """Описание перечня и параметров признаков."""

    tickers: tuple[str, ...]
    last_date: datetime
    close: bool
    div: bool
    ret: bool


class Builder:
    """Создает Datasets для всех тикеров."""

    def __init__(
        self,
        data_adapter: MarketData,
    ) -> None:
        self._data_adapter = data_adapter

    async def build(
        self,
        feats: Features,
        days: Days,
    ) -> list[OneTickerData]:
        """Создает Datasets для всех тикеров."""
        prices = await self._data_adapter.price(feats.last_date, feats.tickers)

        aws = [
            self._prepare_features(
                ticker,
                feats,
                days,
                prices[ticker].dropna(),
            )
            for ticker in feats.tickers
        ]

        return await asyncio.gather(*aws)

    async def _prepare_features(
        self,
        ticker: str,
        feats: Features,
        days: Days,
        price: pd.Series,
    ) -> OneTickerData:
        price_prev = price.shift(1).iloc[1:]
        price = price.iloc[1:]

        df_div = await self._prepare_div(ticker, price.index)

        ret_total = (price + df_div).div(price_prev).sub(1)

        features = []

        if feats.ret:
            features.append(ret_total)

        if feats.close:
            features.append(price.div(price_prev).sub(1))

        if feats.div:
            features.append(df_div.div(price_prev))

        return OneTickerData(
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
