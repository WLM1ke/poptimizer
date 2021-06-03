"""Динамика максимальной цены."""
import pandas as pd
import torch

from poptimizer.config import DEVICE
from poptimizer.data.views import quotes
from poptimizer.dl.features.data_params import DataParams
from poptimizer.dl.features.feature import Feature, FeatureType
from poptimizer.shared import col


class High(Feature):
    """Динамика максимальной цены, нормированная на начальную цену закрытия.

    Максимальная цена содержит дополнительную информацию о динамике стоимости актива и его внутридневной
    волатильности.
    """

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        p_high = quotes.prices(params.tickers, params.end, col.HIGH)[ticker]
        price = params.price(ticker)
        p_high = p_high.reindex(
            price.index,
            method="ffill",
            axis=0,
        )
        self.high = torch.tensor(p_high.values, dtype=torch.float, device=DEVICE)
        self.price = torch.tensor(params.price(ticker).values, dtype=torch.float, device=DEVICE)
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        return self.high[item : item + self.history_days] / self.price[item] - 1

    @property
    def type_and_size(self) -> tuple[FeatureType, int]:
        """Тип признака и размер признака."""
        return FeatureType.SEQUENCE, self.history_days
