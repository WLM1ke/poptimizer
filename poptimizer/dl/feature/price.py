"""Динамика изменения цены нормированная на первоначальную цену."""
import torch

from poptimizer.dl.feature.feature import Feature
from poptimizer.dl.params import ModelParams


class Prices(Feature):
    """Динамика изменения цены нормированная на первоначальную цену."""

    def __init__(self, ticker: str, params: ModelParams):
        super().__init__(ticker, params)
        self.price = torch.tensor(params.price(ticker))
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        price = self.price
        return price[item : item + history_days] / price[item] - 1
