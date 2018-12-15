"""Составляет ML-прогноз."""
from abc import ABC
from typing import Tuple

import numpy as np
import pandas as pd


class AbstractForecast(ABC):
    """Класс с прогнозом."""

    # Словарь с параметрами ML-модели данных
    PARAMS = None

    def __init__(self, tickers: Tuple[str], date: pd.Timestamp):
        self._tickers = tickers
        self._date = date

    @property
    def date(self) -> pd.Timestamp:
        return self._date

    @property
    def tickers(self) -> Tuple[str]:
        self._tickers

    @property
    def mean(self) -> np.array:
        pass

    @property
    def cov(self) -> np.array:
        pass
