"""Признак - доходность за последний год."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin


class Mom12m(DaysParamsMixin, AbstractFeature):
    """12-month momentum - средняя доходность примерно за 12 предыдущих месяцев.

    Аномальная доходность акций, продемонстрировавших максимальный рост за последние 12 месяцев,
    отмечается во множестве исследований. Данный эффект носит устойчивый характер и максимальную силу
    обычно имеет для доходности за 9-16 предыдущих месяцев.

    При оптимизации гиперпараметров выбирается оптимальное количество торговых дней для расчета
    моментума.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        params = params or self._params
        days = params["days"]
        returns = data.log_total_returns(self._tickers, self._last_date)
        mom12m = returns.rolling(days).mean()
        mom12m = mom12m.stack()
        mom12m.name = self.name
        return mom12m
