"""Составляет ML-прогноз."""
from abc import ABC
from typing import Tuple

import numpy as np
import pandas as pd

from poptimizer import data
from poptimizer.ml import examples, ledoit_wolf
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS


class AbstractForecast(ABC):
    """Класс с прогнозом."""

    # Параметры ML-модели данных
    DATA, MODEL = (None, None)

    def __init__(self, tickers: Tuple[str, ...], date: pd.Timestamp):
        self._tickers = tickers
        self._date = date
        self._examples = examples.Examples(tickers, date)

    @property
    def mean(self) -> np.array:
        """Ожидаемая доходность."""
        return

    @property
    def cov(self) -> np.array:
        """Ковариационная матрица."""
        days = self._examples.std_days(self.DATA)
        returns = data.log_total_returns(self._tickers, self._date)
        returns = returns.iloc[-days:,]
        cov = ledoit_wolf.shrinkage(returns.values)
        return cov * YEAR_IN_TRADING_DAYS
        # Тут должно умножаться на качество предсказания или
        # качество предсказания в квадрате
        # и пересчет на степени свободы n / (n - 1)
