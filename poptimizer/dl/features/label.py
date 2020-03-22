"""Метка данных."""
from abc import ABC

import torch

from poptimizer.dl.data_params import DataParams
from poptimizer.dl.features.feature import Feature


class Label(Feature, ABC):
    """Метка линейная комбинация полной и дивидендной доходности с суммарным весом 1."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        div = torch.tensor(params.div(ticker).values, dtype=torch.float)
        self.cum_div = torch.cumsum(div, dim=0)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float)
        self.history_days = params.history_days
        self.forecast_days = params.forecast_days
        self.div_share = params.get_feat_params(self.name)["div_share"]

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        forecast_days = self.forecast_days
        price = self.price
        div = self.cum_div

        last_history_price = price[item + history_days - 1]
        last_history_div = div[item + history_days - 1]
        last_forecast_price = price[item + history_days - 1 + forecast_days]
        last_forecast_div = div[item + history_days - 1 + forecast_days]

        div = last_forecast_div - last_history_div
        price_growth = (last_forecast_price - last_history_price) * (1 - self.div_share)
        label = (price_growth + div) / last_history_price
        return label.reshape(-1)

    @staticmethod
    def key() -> str:
        """Ключ по которому нужно сохранять признак."""
        return "Label"

    @staticmethod
    def unique() -> bool:
        """Является ли признак единственным для данного ключа."""
        return True
