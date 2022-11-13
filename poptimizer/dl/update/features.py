"""Сервис обновления признаков."""
import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

import pandas as pd
import torch
from pydantic import root_validator

from poptimizer.core import consts, domain, repository
from poptimizer.data.adapter import MarketData
from poptimizer.portfolio.adapter import PortfolioData


class Numerical(str, Enum):  # noqa: WPS600
    """Наименование количественных признаков."""

    RETURNS = "Returns"
    DIVIDENDS = "Dividends"


class Categorical(str, Enum):  # noqa: WPS600
    """Наименование категориальных признаков."""


class Features(domain.BaseEntity):
    """Набор признаков DL-модели для заданного тикера."""

    group: ClassVar[domain.Group] = domain.Group.FEATURES
    ret: list[float]
    num: dict[Numerical, list[float]]
    cat: dict[Categorical, list[int]]

    @property
    def returns(self) -> torch.Tensor:
        """Доходности для ковариации - shape(timestamps,)."""
        return torch.tensor(
            self.returns,
            dtype=torch.float,
            device=consts.DEVICE,
        )

    @property
    def numerical(self) -> torch.Tensor:
        """Количественные признаки - shape(n_feat, timestamps)."""
        return torch.tensor(
            [self.num[feat] for feat in Numerical],
            dtype=torch.float,
            device=consts.DEVICE,
        )

    @property
    def categorical(self) -> torch.Tensor:
        """Категориальные признаки - shape(n_feat, timestamps)."""
        return torch.tensor(
            [self.cat[feat] for feat in Categorical],
            dtype=torch.int,
            device=consts.DEVICE,
        )

    @root_validator
    def _num_features_have_equal_length(cls, attr_dict: dict[str, Any]) -> dict[str, Any]:
        if len(Numerical) != len(attr_dict["num"]):
            raise ValueError("wrong amount of numerical features")

        days = len(attr_dict["ret"])

        for feat in Numerical:
            if days != len(attr_dict["num"][feat]):
                raise ValueError(f"wrong amount of days in {feat}")

        return attr_dict

    @root_validator
    def _cat_features_have_equal_length(cls, attr_dict: dict[str, Any]) -> dict[str, Any]:
        if len(Categorical) != len(attr_dict["cat"]):
            raise ValueError("wrong amount of categorical features")

        days = len(attr_dict["ret"])

        for feat in Categorical:
            if days != len(attr_dict["cat"][feat]):
                raise ValueError(f"wrong amount of days in {feat}")

        return attr_dict


class Service:
    """Сервис обновления признаков."""

    def __init__(
        self,
        repo: repository.Repo,
        data_adapter: MarketData,
        port_adapter: PortfolioData,
    ) -> None:
        self._logger = logging.getLogger("Features")
        self._repo = repo
        self._data_adapter = data_adapter
        self._port_adapter = port_adapter

    async def update(self, update_day: datetime) -> None:
        """Обновляет значение признаков."""
        await self._update(update_day)

        self._logger.info("update is completed")

    async def _update(self, update_day: datetime) -> None:
        tickers = await self._port_adapter.tickers()
        prices = await self._data_adapter.price(update_day, tickers)

        aws = [
            self._update_for_ticker(
                update_day,
                ticker,
                prices[ticker].dropna(),
            )
            for ticker in tickers
        ]
        await asyncio.gather(*aws)

    async def _update_for_ticker(self, update_day: datetime, ticker: str, df_price: pd.Series) -> None:
        prev_price = df_price.shift(1).iloc[1:]
        df_price = df_price.iloc[1:]

        df_div = await self._prepare_div(ticker, df_price.index)

        feat = Features(
            id_=ticker,
            timestamp=update_day,
            ret=(df_price + df_div).div(prev_price).sub(1).to_list(),
            num={
                Numerical.RETURNS: df_price.div(prev_price).sub(1).to_list(),
                Numerical.DIVIDENDS: df_div.div(prev_price).to_list(),
            },
            cat={},
        )

        await self._repo.save(feat)

    async def _prepare_div(self, ticker: str, index: pd.DatetimeIndex) -> pd.Series:
        first_day = index[1]
        last_day = index[-1] + 2 * pd.tseries.offsets.BDay()

        df_div = pd.Series(0, index=index)

        async for date, div in self._data_adapter.dividends(ticker):
            if date < first_day or date >= last_day:
                continue

            loc = index.get_indexer([date], method="ffill")[0]
            df_div.iat[loc - 1] += div * consts.AFTER_TAX

        return df_div
