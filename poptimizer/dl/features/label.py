"""Метка данных."""
from typing import Tuple

import torch

from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType


class Label(Feature):
    """Метка - полная доходность за определенный период."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        div = torch.tensor(params.div(ticker).values, dtype=torch.float)
        self.cum_div = torch.cumsum(div, dim=0)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float)
        self.history_days = params.history_days
        self.forecast_days = params.forecast_days

    def __getitem__(self, item: int) -> torch.Tensor:
        price = self.price
        div = self.cum_div

        start = item + self.history_days - 1
        last_history_price = price[start]
        last_history_div = div[start]

        end = start + self.forecast_days
        last_forecast_price = price[end]
        last_forecast_div = div[end]

        div = last_forecast_div - last_history_div
        price_growth = last_forecast_price - last_history_price
        label = (price_growth + div) / last_history_price
        return label.reshape(-1)

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.LABEL, self.forecast_days
