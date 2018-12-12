"""Признак - доходность за последние торговые дни."""
import pandas as pd

from poptimizer import data
from poptimizer.ml.feature import AbstractFeature
from poptimizer.ml.label import YEAR_IN_TRADING_DAYS


class Mean(AbstractFeature):
    """Доходность за несколько предыдущих дней в годовом выражении.

    В перспективе можно организовать поиск по количеству предыдущих дней.
    """

    def get(self, days: int = YEAR_IN_TRADING_DAYS) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        returns = data.log_total_returns(self._tickers, self._date)
        mean = returns.rolling(days, min_periods=days).mean() * YEAR_IN_TRADING_DAYS
        mean = mean.stack()
        mean.name = "MEAN"
        return mean

    @staticmethod
    def is_categorical() -> bool:
        """Не категориальный признак."""
        return False

    def get_param_space(self) -> dict:
        """Параметров нет - пустой словарь."""
        return dict()

    def check_bounds(self, *kwargs):
        """Параметров нет, поэтому в проверке нет необходимости."""
