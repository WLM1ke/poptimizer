"""Признак - минимум дневной доходности за последний месяц."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.config import MIN1M_RANGE
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin


class Min1m(DaysParamsMixin, AbstractFeature):
    """1-month minimum - минимальная доходность примерно за 1 предыдущий месяц.

    Резко падающие акции обычно находятся под прессом плохих новостей в и продолжают падение в течении
    некоторого периода и обладают повышенной волатильностью.
    """

    RANGE = MIN1M_RANGE

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._returns = data.log_total_returns(tickers, last_date)

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        mean = returns.iloc[loc - days + 1 : loc + 1].min(axis=0, skipna=False)
        mean.name = self.name
        return mean
