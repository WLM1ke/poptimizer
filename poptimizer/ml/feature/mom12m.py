"""Признак - доходность за последний год."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysPeriodsParamsMixin


class Mom12m(DaysPeriodsParamsMixin, AbstractFeature):
    """12-month momentum - средняя доходность примерно за 12 предыдущих месяцев.

    Аномальная доходность акций, продемонстрировавших максимальный рост за последние 12 месяцев,
    отмечается во множестве исследований. Данный эффект носит устойчивый характер и максимальную силу
    обычно имеет для доходности за 9-16 предыдущих месяцев.

    При оптимизации гиперпараметров выбирается оптимальное количество торговых дней для расчета
    моментума и разбиение на подпериоды.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        params = params or self._params
        periods = params["periods"]
        days = params["days"] // periods
        returns = data.log_total_returns(self._tickers, self._last_date)
        mom12m = returns.rolling(days).sum()
        r_periods = []
        for i in range(periods):
            r_i = mom12m.shift(i * days)
            r_i = r_i.stack()
            r_i.name = f"{self.name}_{i}"
            r_periods.append(r_i)
        return pd.concat(r_periods, axis=1)
