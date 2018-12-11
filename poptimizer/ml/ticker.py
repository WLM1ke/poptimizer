"""Признак - тикер."""
import pandas as pd

from poptimizer import data
from poptimizer.ml.feature import AbstractFeature
from poptimizer.store import TICKER


class Ticker(AbstractFeature):
    """Тикер для каждой даты из котировок."""

    def get(self):
        """Для дат, в которые есть котировки указывается тикер."""
        prices = data.prices(self._tickers, self._date)
        prices = prices.stack()
        tickers = prices.index.droplevel(0)
        return pd.DataFrame(data=tickers, index=prices.index, columns=[TICKER])

    @staticmethod
    def is_categorical() -> bool:
        """Категориальный признак."""
        return True

    def get_param_space(self) -> dict:
        """Параметров нет - пустой словарь."""
        return dict()

    def check_bounds(self, *kwargs):
        """Параметров нет, поэтому в проверке нет необходимости."""
