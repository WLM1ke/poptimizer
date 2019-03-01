"""Признак - тикер."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature


class Ticker(AbstractFeature):
    """Тикер для каждой даты из котировок.

    Позволяет отразить специфические черты отдельных бумаг.
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)
        self._returns = data.log_total_returns(tickers, last_date)

    @staticmethod
    def is_categorical() -> bool:
        """Категориальный признак."""
        return True

    @classmethod
    def get_params_space(cls) -> dict:
        """Параметров нет - пустой словарь."""
        return dict()

    def get(self, params=None) -> pd.Series:
        """Для дат, в которые есть котировки указывается тикер."""
        returns = self._returns.stack()
        returns.loc[:] = returns.index.get_level_values(1)
        return returns
