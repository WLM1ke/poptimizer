"""Динамика индекса волатильности MCFTRR."""
from typing import Tuple

import torch

from poptimizer.data.views import indexes
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.config import DEVICE


class MCFTRR(Feature):
    """Динамика индекса полной доходности MCFTRR нормированная на начальную дату.

    Динамика индекса отражает общую рыночную конъюнктуру, в рамках которой осуществляется
    прогнозирование доходности конкретного инструмента.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        mcftrr = indexes.mcftrr(params.end)
        price = params.price(ticker)
        mcftrr = mcftrr.reindex(
            price.index,
            method="ffill",
            axis=0,
        )
        self.mcftrr = torch.tensor(mcftrr.values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.mcftrr[item : item + self.history_days] / self.mcftrr[item] - 1

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
