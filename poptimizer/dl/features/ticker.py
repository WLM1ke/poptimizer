"""Номер тикера данного примера."""
from typing import Tuple

import torch

from poptimizer.config import DEVICE
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType


class Ticker(Feature):
    """Номер тикера среди упорядоченной по алфавиту последовательности тикеров в портфеле."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        tickers = params.tickers
        self._num_tickers = len(tickers)
        self._idx = torch.tensor(tickers.index(ticker), dtype=torch.long, device=DEVICE)

    def __getitem__(self, item: int) -> torch.Tensor:
        return self._idx

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.EMBEDDING, self._num_tickers
