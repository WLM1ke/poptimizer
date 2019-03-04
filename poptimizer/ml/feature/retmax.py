"""Признак - максимум дневной доходности за последний месяц."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin


class RetMax(DaysParamsMixin, AbstractFeature):
    """Maximum daily return - максимальная доходность примерно за 1 предыдущий месяц.

    Акции демонстрирующие резкий рост за последнее время похожи на лотерейные билеты - привлекают
    повышенное внимание отдельных категорий мелких инвесторов, склонных к игровому поведению, и обычно
    имеют значимо более низкую доходность в последующие месяцы.
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """Максимальная доходность за указанное количество предыдущих дней."""
        params = params or self._params
        days = params["days"]
        returns = data.log_total_returns(self._tickers, self._last_date)
        retmax = returns.rolling(days).max()
        retmax = retmax.stack()
        retmax.name = self.name
        return retmax
