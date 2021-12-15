"""Представление прогноза."""
import dataclasses

import numpy as np
import pandas as pd

from poptimizer.dl.ledoit_wolf import ledoit_wolf_cor


@dataclasses.dataclass
class Forecast:
    """Прогноз доходности и ковариации."""

    tickers: tuple[str, ...]
    date: pd.Timestamp
    history_days: int
    mean: pd.Series
    std: pd.Series
    cov: np.array = dataclasses.field(init=False)
    cor: float = dataclasses.field(init=False)
    shrinkage: float = dataclasses.field(init=False)
    risk_aversion: float
    error_tolerance: float

    def __post_init__(self):
        sigma, self.cor, self.shrinkage = ledoit_wolf_cor(self.tickers, self.date, self.history_days)
        std = self.std.values
        self.cov = std.reshape(1, -1) * sigma * std.reshape(-1, 1)
