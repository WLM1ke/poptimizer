"""Признак - дивиденды за последние периоды."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature import AbstractFeature
from poptimizer.store import DIVIDENDS_START

YEAR_IN_DAYS = 366


class Dividends(AbstractFeature):
    """Дивиденды за последние календарные дни.

    Пока 366, но в перспективе возможна оптимизация.
    Кроме того еще и выбор количества периодов.
    """

    def __init__(self, tickers: Tuple[str], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._dividends = data.dividends(tickers, last_date)
        self._prices = data.prices(tickers, last_date)

    @staticmethod
    def is_categorical() -> bool:
        """Количественный признак."""
        return False

    @classmethod
    def get_params_space(cls) -> dict:
        """Фиксированный параметр - количество календарных дней для расчета дивидендов."""
        return dict(days=YEAR_IN_DAYS)

    def check_bounds(self, **kwargs):
        """Параметры константные, поэтому в проверке нет необходимости."""

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Дивидендная доходность за несколько предыдущих дней."""
        days = kwargs["days"]
        start = date - pd.DateOffset(days=days)
        if start >= DIVIDENDS_START:
            dividends = self._dividends.loc[start:date].sum(axis=0)
            prices = self._prices.loc[date]
            yields = dividends / prices
            yields.name = "DIVIDENDS"
            return yields
        return pd.Series(index=list(self._tickers))
