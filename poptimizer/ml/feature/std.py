"""Признак - СКО за последние торговые дни."""
from typing import Tuple

import pandas as pd
from hyperopt import hp

from poptimizer import data
from poptimizer.ml.feature import label
from poptimizer.ml.feature.feature import AbstractFeature

# Диапазон поиска количества дней
RANGE = [193, 258]


class STD(AbstractFeature):
    """СКО за несколько предыдущих дней.

    СКО выступает в двоякой роли. С одной стороны, доходности акций обладают явной
    гетероскедастичностью и варьируются от одной акции к другой, поэтому для получения меток данных  с
    одинаковой волатильностью целесообразно нормировать доходность по предыдущей волатильности. С
    другой стороны, сама волатильность является является известным фактором, объясняющим доходность,
    так называемая low-volatility anomaly.

    В целях нормировки доходности в большинстве случаев оптимальным считается оценка волатильности за
    последние 8-12 месяцев. Оптимальный период выбирается при поиске гиперпараметров.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._returns = data.log_total_returns(tickers, last_date)

    @staticmethod
    def is_categorical() -> bool:
        """Не категориальный признак."""
        return False

    @classmethod
    def get_params_space(cls) -> dict:
        """Значение дней в диапазоне."""
        return {"days": hp.choice("std", list(range(*RANGE)))}

    def check_bounds(self, **kwargs):
        """Рекомендация по расширению интервала."""
        days = kwargs["days"]
        label.check_bounds(f"{self.name}.RANGE", days, RANGE)

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """СКО за указанное количество предыдущих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        std = returns.iloc[loc - days + 1 : loc + 1].std(axis=0, skipna=False)
        std.name = self.name
        return std
