"""Признак - тикер."""
from typing import Tuple

import pandas as pd

from poptimizer.ml.feature.feature import AbstractFeature


class Ticker(AbstractFeature):
    """Тикер для каждой даты из котировок."""

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)

    @staticmethod
    def is_categorical() -> bool:
        """Категориальный признак."""
        return True

    @classmethod
    def get_params_space(cls) -> dict:
        """Параметров нет - пустой словарь."""
        return dict()

    def check_bounds(self, *kwargs):
        """Параметров нет, поэтому в проверке нет необходимости."""

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Для дат, в которые есть котировки указывается тикер."""
        tickers = self._tickers
        return pd.Series(data=tickers, index=tickers, name=self.name)
