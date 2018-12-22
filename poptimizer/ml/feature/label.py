"""Метки для обучения."""
from typing import Tuple

import pandas as pd
from hyperopt import hp

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature

YEAR_IN_TRADING_DAYS = 12 * 21

# Диапазон поиска количества дней
RANGE = [21, 54]


def check_bounds(name, days, interval, bound: float = 0.1, increase: float = 0.2):
    """Предложение по расширению интервала"""
    lower, upper = interval
    if days / (1 + bound) < lower:
        print(
            f"\nНеобходимо расширить {name} до [{days / (1 + increase):.0f}, {upper}]"
        )
    elif days * (1 + bound) > upper:
        print(
            f"\nНеобходимо расширить {name} до [{lower}, {days * (1 + increase):.0f}]"
        )


class Label(AbstractFeature):
    """Метка для обучения - средняя доходность за несколько следующих дней.


    Обычно в академических исследования исследованиях ориентируются на ежемесячную доходность,
    однако в ряд признаков имеет более высокую предсказательную способность на других временных
    интервалах. Так большинство метрик, основывающихся на истории цен, имеют максимальную
    предсказательную способность в интервале от 1 до 6 месяцев, а на фундаментальных факторах часто
    максимальная предсказательная способность наблюдается для доходности в следующие несколько лет.

    Использованием длительных периодов для предсказания существенно сокращает количество обучающих
    примеров, поэтому для российского рынка целесообразно ограничиться периодом прогнозирования от
    месяца до нескольких месяцев. Оптимальный прогнозный период выбирается при поиске гиперпараметров.
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
        """Рекомендация по расширению интервала."""
        days = kwargs["days"]
        check_bounds(f"{self.name}.RANGE", days, RANGE)

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
