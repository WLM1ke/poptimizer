"""Динамика цены открытия."""
from typing import Tuple

import torch

from poptimizer.config import DEVICE
from poptimizer.data.views import quotes
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.shared import col


class Open(Feature):
    """Динамика цены открытия, нормированная на начальную цену закрытия.

    Цена открытия содержит дополнительную информацию о динамике стоимости актива и его внутридневной
    волатильности.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        p_open = quotes.prices(params.tickers, params.end, col.OPEN)[ticker]
        price = params.price(ticker)
        p_open = p_open.reindex(
            price.index,
            method="ffill",
            axis=0,
        )
        self.open = torch.tensor(p_open.values, dtype=torch.float, device=DEVICE)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.open[item : item + self.history_days] / self.price[item] - 1

    @property
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
