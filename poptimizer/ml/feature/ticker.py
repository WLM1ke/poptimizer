"""Признак - тикер."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, ON_OFF


class Ticker(AbstractFeature):
    """Тикер для каждой даты из котировок.

    Позволяет отразить специфические черты отдельных бумаг.
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    @staticmethod
    def is_categorical() -> bool:
        """Категориальный признак."""
        return True

    @classmethod
    def get_params_space(cls) -> dict:
        """Параметров нет - пустой словарь."""
        return {ON_OFF: True}

    def get(self, params=None) -> pd.Series:
        """Для дат, в которые есть котировки указывается тикер."""
        returns = data.log_total_returns(self._tickers, self._last_date)
        tickers = returns.stack()
        tickers.loc[:] = tickers.index.get_level_values(1)
        tickers.name = self.name
        return tickers
