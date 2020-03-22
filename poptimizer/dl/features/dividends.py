"""Динамика накопленных дивидендов нормированная на первоначальную цену."""
import torch

from poptimizer.dl.data_params import DataParams
from poptimizer.dl.features.feature import Feature
from poptimizer.dl.features.prices import SequenceMixin


class Dividends(SequenceMixin, Feature):
    """Динамика накопленных дивидендов нормированная на первоначальную цену."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        self.div = torch.tensor(params.div(ticker).values, dtype=torch.float)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return (
            self.div[item : item + self.history_days].cumsum(dim=0) / self.price[item]
        )
