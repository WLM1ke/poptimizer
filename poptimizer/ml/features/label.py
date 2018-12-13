"""Метки для обучения."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.features.feature import AbstractFeature

YEAR_IN_TRADING_DAYS = 12 * 21


class Label(AbstractFeature):
    """Доходность за несколько следующих дней в годовом выражении.

    В перспективе можно организовать поиск по количеству следующих дней.
    """

    def __init__(self, tickers: Tuple[str], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._returns = data.log_total_returns(tickers, last_date)

    @staticmethod
    def is_categorical() -> bool:
        """Не категориальный признак."""
        return False

    @classmethod
    def get_params_space(cls) -> dict:
        """Фиксированный параметр - количество дней для расчета доходности."""
        return dict(days=21)

    def check_bounds(self, **kwargs):
        """Параметры константные, поэтому в проверке нет необходимости."""

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Средняя доходность за указанное количество следующих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        mean = returns.iloc[loc + 1 : loc + days + 1].mean(axis=0)
        mean.name = "LABEL"
        return mean * YEAR_IN_TRADING_DAYS
