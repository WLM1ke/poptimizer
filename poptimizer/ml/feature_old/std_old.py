"""Признак - СКО за последние торговые дни."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.config import STD_RANGE
from poptimizer.ml.feature_old.feature_old import AbstractFeature, DaysParamsMixin


class STD(DaysParamsMixin, AbstractFeature):
    """Accrual volatility - СКО за примерно 12 предыдущих месяцев.

    СКО выступает в двоякой роли. С одной стороны, доходности акций обладают явной
    гетероскедастичностью и варьируются от одной акции к другой, поэтому для получения меток данных  с
    одинаковой волатильностью целесообразно нормировать доходность по предыдущей волатильности. С
    другой стороны, сама волатильность является является известным фактором, объясняющим доходность,
    так называемая low-volatility anomaly.

    В целях нормировки доходности в большинстве случаев оптимальным считается оценка волатильности за
    последние 8-12 месяцев. Оптимальный период выбирается при поиске гиперпараметров.
    """

    RANGE = STD_RANGE

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._returns = data.log_total_returns(tickers, last_date)

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """СКО за указанное количество предыдущих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        std = returns.iloc[loc - days + 1 : loc + 1].std(axis=0, skipna=False)
        std.name = self.name
        return std
