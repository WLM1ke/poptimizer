"""Метки для обучения."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin

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

    # noinspection PyUnresolvedReferences
    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """Средняя доходность за указанное количество следующих дней."""
        params = params or self._params
        days = params["days"]
        returns = data.log_total_returns(self._tickers, self._last_date)
        label = returns.rolling(days).mean()
        label = label.shift(-days).stack()
        label.name = self.name
        return label
