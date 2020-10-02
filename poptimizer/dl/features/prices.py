"""Динамика изменения цены нормированная на первоначальную цену."""
from typing import Tuple

import torch

from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.config import DEVICE


class Prices(Feature):
    """Динамика изменения цены нормированная на первоначальную цену."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        price = self.price
        return price[item : item + history_days] / price[item] - 1

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
