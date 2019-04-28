"""Фактор - ускорение среднесрочного моментума."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin


class ChMom6m(DaysParamsMixin, AbstractFeature):
    """Change in 6-month momentum - ускорение роста за 6 месяцев.

    Акции, рост которых ускорился за последние шесть месяцев по сравнению с предыдущим шестимесячным
    периодом демонстрируют аномальную доходность в последующий период. Фактор близок по сути к
    обычному моментому, и по сути является его первой производной.

    При оптимизации гиперпараметров выбирается оптимальное количество торговых дней для расчета.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        params = params or self._params
        days = params["days"]
        returns = data.log_total_returns(self._tickers, self._last_date)
        mom6m = returns.rolling(days).mean()
        mom6m_prev = mom6m.shift(days)
        mom6m = mom6m - mom6m_prev
        mom6m = mom6m.stack()
        mom6m.name = self.name
        return mom6m
