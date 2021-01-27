"""Тип ценной бумаги."""
from typing import Tuple

import torch

from poptimizer.data.views import moex
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.config import DEVICE
from poptimizer.shared import col


class TickerType(Feature):
    """Номер типа инструмента.

    На MOEX обращаются несколько типов инструментов (обыкновенные и привилегированный акции российских
    эмитентов, ETF и акции иностранных эмитентов). Разные типы инструментов могут иметь особенности с
    точки зрения ожидаемой доходности, волатильности и влияния рыночных факторов.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        ticker_type = moex.ticker_types()[ticker]
        self._ticker_type = torch.tensor(ticker_type, dtype=torch.long, device=DEVICE)

    def __getitem__(self, item: int) -> torch.Tensor:
        return self._ticker_type

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.EMBEDDING, col.TYPES_N
