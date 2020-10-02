"""Номер дня в году."""
from typing import Tuple

import torch

from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.config import DEVICE


class DayOfYear(Feature):
    """Номер дня в году начиная с нуля для каждого момента времени.

    Выплаты дивидендов сконцентрированы в определенные периода времени, а доходности имеют аномалии,
    связанные с концом года и кварталов.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)

        day_of_year = params.price(ticker).index.dayofyear - 1
        self.day_of_year = torch.tensor(day_of_year, dtype=torch.long, device=DEVICE)

        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.day_of_year[item : item + self.history_days]

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.EMBEDDING_SEQUENCE, 366
