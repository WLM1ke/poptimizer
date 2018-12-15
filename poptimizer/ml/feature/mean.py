"""Признак - доходность за последние торговые дни."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


class Mean(AbstractFeature):
    """Доходность за несколько предыдущих торговых дней в годовом выражении.

    В перспективе можно организовать поиск по количеству предыдущих дней.
    Кроме того еще и выбор количества периодов.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._returns = data.log_total_returns(tickers, last_date)

    @staticmethod
    def is_categorical() -> bool:
        """Не категориальный признак."""
        return False

    @classmethod
    def get_params_space(cls) -> dict:
        """Фиксированный параметр - количество дней для расчета среднего."""
        return dict(days=YEAR_IN_TRADING_DAYS)

    def check_bounds(self, **kwargs):
        """Параметры константные, поэтому в проверке нет необходимости."""

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        mean = returns.iloc[loc - days + 1 : loc + 1].mean(axis=0)
        mean.name = self.name
        return mean * YEAR_IN_TRADING_DAYS
