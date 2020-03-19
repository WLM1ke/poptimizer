"""Динамика изменения цены нормированная на первоначальную цену."""
import torch

from poptimizer.dl.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureTypes


class Prices(Feature):
    """Динамика изменения цены нормированная на первоначальную цену."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        price = self.price
        return price[item : item + history_days] / price[item] - 1

    @property
    def type(self) -> FeatureTypes:
        """Численные данные."""
        return FeatureTypes.NUMERICAL
