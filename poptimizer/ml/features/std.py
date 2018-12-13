"""Признак - СКО за последние торговые дни."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.features.feature import AbstractFeature
from poptimizer.ml.features.label import YEAR_IN_TRADING_DAYS


class STD(AbstractFeature):
    """СКО за несколько предыдущих дней в годовом выражении.

    В перспективе можно организовать поиск по количеству предыдущих дней.
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
        """Фиксированный параметр - количество дней для расчета СКО."""
        return dict(days=YEAR_IN_TRADING_DAYS)

    def check_bounds(self, **kwargs):
        """Параметры константные, поэтому в проверке нет необходимости."""

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """СКО за указанное количество предыдущих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        std = returns.iloc[loc - days + 1 : loc + 1].std(axis=0)
        std.name = "STD"
        return std * YEAR_IN_TRADING_DAYS ** 0.5
