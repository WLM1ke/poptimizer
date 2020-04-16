"""Динамика оборота."""
from typing import Tuple

import torch

from poptimizer import data
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType


class Turnover(Feature):
    """Динамика логарифма 1 + оборот."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        price = params.price(ticker)
        turnover = data.turnovers((ticker,), price.index[-1])[ticker]
        turnover = turnover.reindex(price.index, axis=0, fill_value=0)
        turnover = torch.tensor(turnover.values, dtype=torch.float)
        self.turnover = torch.log1p(turnover)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.turnover[item : item + self.history_days]

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
