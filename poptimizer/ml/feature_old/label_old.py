"""Метки для обучения."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.config import LABEL_RANGE
from poptimizer.ml.feature_old.feature_old import AbstractFeature, DaysParamsMixin

YEAR_IN_TRADING_DAYS = 12 * 21


class Label(DaysParamsMixin, AbstractFeature):
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

    RANGE = LABEL_RANGE

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._returns = data.log_total_returns(tickers, last_date)

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
