"""Динамика индекса полной доходности нефтегазовых акций MEOGTRR."""
from typing import Tuple

import torch

from poptimizer.config import DEVICE
from poptimizer.data.views import indexes
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType


class MEOGTRR(Feature):
    """Динамика индекса полной доходности нефтегазовых акций MEOGTRR нормированная на начальную дату."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        index = indexes.index("MEOGTRR", params.end)
        price = params.price(ticker)
        index = index.reindex(
            price.index,
            method="ffill",
            axis=0,
        )
        self.index = torch.tensor(index.values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.index[item : item + self.history_days] / self.index[item] - 1

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
