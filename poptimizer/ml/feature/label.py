"""Метки для обучения."""
from typing import Tuple

import pandas as pd
from hyperopt import hp

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature

YEAR_IN_TRADING_DAYS = 12 * 21

# Диапазон поиска количества дней
RANGE = [21, 33]


class Label(AbstractFeature):
    """Средняя доходность за несколько следующих дней.

    В перспективе можно организовать поиск по количеству следующих дней.
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
        return {"days": hp.choice("label_days", list(range(*RANGE)))}

    def check_bounds(self, **kwargs):
        """Параметры константные, поэтому в проверке нет необходимости."""
        days = kwargs["days"]
        if days / 1.1 < RANGE[0]:
            print(
                f"\nНеобходимо расширить {self.name}.RANGE до [{days / 1.1:.0f}, {RANGE[1]}]"
            )
        elif days * 1.1 > RANGE[1]:
            print(
                f"\nНеобходимо расширить {self.name}.RANGE до [{RANGE[0]}, {days * 1.1:.0f}]"
            )

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Средняя доходность за указанное количество следующих дней."""
        returns = self._returns
        loc = returns.index.get_loc(date)
        days = kwargs["days"]
        mean = returns.iloc[loc + 1 : loc + days + 1].mean(axis=0, skipna=False)
        mean.name = self.name
        return mean

    @property
    def index(self):
        """Индекс используемых данных"""
        return self._returns.index
