"""Динамика индекса курса доллара."""
from typing import Tuple

import torch

from poptimizer.config import DEVICE
from poptimizer.data.views import indexes
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType


class USD(Feature):
    """Динамика индекса доллара нормированная на начальную дату.

    Иностранные и российские бумаги могут существенно по разному реагировать на сильные движения курса
    доллара. Данный признак позволяет выучить такие особенности.
    """

    def __init__(self, ticker: str, params: DataParams):
        """Сохраняет данные о курсе."""
        super().__init__(ticker, params)
        usd = indexes.usd(params.end)
        price = params.price(ticker)
        usd = usd.reindex(
            price.index,
            method="ffill",
            axis=0,
        )
        self.usd = torch.tensor(usd.values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.usd[item : item + self.history_days] / self.usd[item] - 1

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
