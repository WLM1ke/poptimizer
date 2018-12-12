"""Признак - тикер."""
import pandas as pd

from poptimizer import data
from poptimizer.ml.feature import AbstractFeature
from poptimizer.store import TICKER


class Ticker(AbstractFeature):
    """Тикер для каждой даты из котировок."""

    def get(self, *kwargs) -> pd.Series:
        """Для дат, в которые есть котировки указывается тикер."""
        returns = data.log_total_returns(self._tickers, self._date)
        returns = returns.stack()
        tickers = returns.index.droplevel(0)
        return pd.Series(data=tickers, index=returns.index, name=TICKER)

    @staticmethod
    def is_categorical() -> bool:
        """Категориальный признак."""
        return True

    def get_param_space(self) -> dict:
        """Параметров нет - пустой словарь."""
        return dict()

    def check_bounds(self, *kwargs):
        """Параметров нет, поэтому в проверке нет необходимости."""
