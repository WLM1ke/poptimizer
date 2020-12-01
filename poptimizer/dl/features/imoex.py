"""Динамика основного индекса MOEX (без дивидендов)."""
from typing import Tuple

import torch

from poptimizer.data.views import indexes
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.config import DEVICE


class IMOEX(Feature):
    """Динамика основного индекса MOEX нормированная на начальную дату.

    Динамика индекса отражает общую рыночную конъюнктуру, в рамках которой осуществляется
    прогнозирование доходности конкретного инструмента. Хотя индексы полной доходности корректнее
    отражают доход инвестора, многие практики ориентируются скорее на индекс без учета дивидендов.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        imoex = indexes.imoex(params.end)
        price = params.price(ticker)
        imoex = imoex.reindex(price.index, axis=0)
        self.imoex = torch.tensor(imoex.values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.imoex[item : item + self.history_days] / self.imoex[item] - 1

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
