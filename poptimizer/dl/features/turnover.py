"""Динамика оборота."""
from typing import Tuple

import numpy as np
import torch

import poptimizer.data.views.quotes
from poptimizer.data.views import listing
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.config import DEVICE

# Ключ для хранения данных оборота в кеше параметров данных
TURNOVER = "turnover"
AVERAGE_TURNOVER = "average_turnover"


class Turnover(Feature):
    """Динамика логарифма 1 + оборот."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)

        cache = params.cache
        if (turnover := cache.get(TURNOVER)) is None:
            turnover = poptimizer.data.views.quotes.turnovers(params.tickers, params.end)
            cache[TURNOVER] = turnover

        turnover = turnover[ticker]
        price = params.price(ticker)
        turnover = turnover.reindex(price.index, axis=0)
        turnover = torch.tensor(turnover.values, dtype=torch.float, device=DEVICE)
        self.turnover = torch.log1p(turnover)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.turnover[item : item + self.history_days]

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days


class AverageTurnover(Feature):
    """Динамика логарифма 1 + среднего оборота всех бумаг портфеля.

    Использование этого фактора совместно с фактором оборота позволяет выделять вспышки оборота
    специфичные для эмитента.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)

        cache = params.cache
        if (turnover := cache.get(AVERAGE_TURNOVER)) is None:
            if (turnover := cache.get(TURNOVER)) is None:
                turnover = poptimizer.data.views.quotes.turnovers(params.tickers, params.end)
                cache[TURNOVER] = turnover
            turnover = turnover.mean(axis=1)
            turnover = turnover.apply(np.log1p)
            cache[AVERAGE_TURNOVER] = turnover

        price = params.price(ticker)
        turnover = turnover.reindex(price.index, axis=0)
        self.turnover = torch.tensor(turnover.values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.turnover[item : item + self.history_days]

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
