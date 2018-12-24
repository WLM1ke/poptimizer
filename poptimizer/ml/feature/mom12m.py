"""Признак - доходность за последние торговые дни."""
from typing import Tuple

import pandas as pd
from hyperopt import hp

from poptimizer import data
from poptimizer.ml.feature import label
from poptimizer.ml.feature.feature import AbstractFeature

# Диапазон поиска количества дней
RANGE = [229, 310]


class Mom12m(AbstractFeature):
    """Средняя доходность примерно за 12 предыдущих месяцев.

    Аномальная доходность акции, продемонстрировавших максимальный рост за последние 12 месяцев
    отмечается во множестве исследований. Данный эффект носит устойчивый характер и максимальную силу
    обычно имеет для доходности за 9-16 предыдущих месяцев.

    При оптимизации гиперпараметров выбирается оптимальное количество торговых дней для расчета
    моментума.
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
        """Количество дней для расчета моментума."""
        return {"days": hp.choice("mom12m", list(range(*RANGE)))}

    def check_bounds(self, **kwargs):
        """Рекомендация по расширению интервала."""
        days = kwargs["days"]
        label.check_bounds(f"{self.name}.RANGE", days, RANGE)

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        mean = returns.iloc[loc - days + 1 : loc + 1].mean(axis=0, skipna=False)
        mean.name = self.name
        return mean
