"""Динамика накопленных дивидендов нормированная на первоначальную цену."""
from typing import Tuple

import torch

from poptimizer.config import DEVICE
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType


class Dividends(Feature):
    """Динамика накопленных дивидендов нормированная на первоначальную цену."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        self.div = torch.tensor(params.div(ticker).values, dtype=torch.float, device=DEVICE)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return (
            self.div[item : item + self.history_days].cumsum(dim=0) / self.price[item]
        )

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
