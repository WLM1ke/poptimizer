"""Динамика накопленных дивидендов нормированная на первоначальную цену."""
import torch

from poptimizer.dl.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureTypes


class Dividends(Feature):
    """Динамика накопленных дивидендов нормированная на первоначальную цену."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        self.div = torch.tensor(params.div(ticker).values, dtype=torch.float)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.div[item : item + self.history_days] / self.price[item]

    @property
    def type(self) -> FeatureTypes:
        """Численные данные."""
        return FeatureTypes.NUMERICAL
