"""Признак - доходность за последний месяц."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.config import MOM1M_RANGE
from poptimizer.ml.feature_old.feature_old import AbstractFeature, DaysParamsMixin


class Mom1m(DaysParamsMixin, AbstractFeature):
    """1-month momentum - средняя доходность примерно за 1 предыдущий месяц.

    Хотя в общем акции демонстрируют сохранение роста, если они росли в предыдущие периоды,
    на горизонте в один-два месяца эта зависимость обычно нарушается - short term reversal.

    При оптимизации гиперпараметров выбирается оптимальное количество торговых дней для расчета
    краткосрочной реверсии.
    """

    RANGE = MOM1M_RANGE

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._returns = data.log_total_returns(tickers, last_date)

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        mean = returns.iloc[loc - days + 1 : loc + 1].mean(axis=0, skipna=False)
        mean.name = self.name
        return mean
