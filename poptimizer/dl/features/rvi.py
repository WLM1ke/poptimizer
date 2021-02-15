"""Динамика индекса волатильности RVI."""
from typing import Tuple

import torch

from poptimizer.data.views import indexes
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.config import DEVICE


class RVI(Feature):
    """Динамика индекса волатильности RVI.

    Индекс отражает ожидание участников рынка относительно волатильности в ближайший месяц, что может
    быть полезно для прогнозирования волатильности отдельных бумаг.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        rvi = indexes.rvi(params.end)
        price = params.price(ticker)
        rvi = rvi.reindex(
            price.index,
            method="ffill",
            axis=0,
        )
        self.rvi = torch.tensor(rvi.values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.rvi[item : item + self.history_days]

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
