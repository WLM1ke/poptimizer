"""Представление прогноза."""
import dataclasses
from typing import Tuple

import numpy as np
import pandas as pd

import poptimizer.data.views.quotes
from poptimizer.data.views import listing
from poptimizer.dl import ledoit_wolf


def ledoit_wolf_cor(
    tickers: tuple, date: pd.Timestamp, history_days: int
) -> Tuple[np.array, float, float]:
    """Корреляционная матрица на основе Ledoit Wolf."""
    div, p1 = poptimizer.data.views.quotes.div_and_prices(tickers, date)
    p0 = p1.shift(1)
    returns = (p1 + div) / p0
    returns = returns.iloc[-history_days:]
    returns = (returns - returns.mean()) / returns.std(ddof=0)
    return ledoit_wolf.shrinkage(returns.values)


@dataclasses.dataclass
class Forecast:
    """Прогноз доходности и ковариации."""

    tickers: Tuple[str, ...]
    date: pd.Timestamp
    history_days: int
    mean: pd.Series
    std: pd.Series
    cov: np.array = dataclasses.field(init=False)
    cor: float = dataclasses.field(init=False)
    shrinkage: float = dataclasses.field(init=False)

    def __post_init__(self):
        sigma, self.cor, self.shrinkage = ledoit_wolf_cor(self.tickers, self.date, self.history_days)
        std = self.std.values
        self.cov = std.reshape(1, -1) * sigma * std.reshape(-1, 1)
