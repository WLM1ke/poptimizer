"""Вес данного примера."""
from typing import Tuple

import torch

from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.ml.feature.std import LOW_STD


class Weight(Feature):
    """Обратная величина квадрата СКО полной доходности обрезанная для низких значений."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        self.div = torch.tensor(params.div(ticker).values, dtype=torch.float)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        price = self.price
        div = self.div

        price1 = price[item + 1 : item + history_days]
        div = div[item + 1 : item + history_days]
        price0 = price[item : item + history_days - 1]
        returns = (price1 + div) / price0

        std = torch.std(returns, dim=0, keepdim=True, unbiased=True)
        std = torch.max(std, torch.tensor(LOW_STD))
        return std ** -2

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.WEIGHT, self.history_days
