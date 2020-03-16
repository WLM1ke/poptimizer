"""Признак - СКО за последние торговые дни."""
from typing import Tuple

import numpy as np
import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin

# Обрезка совсем маленьких значений, чтобы не было переполнения при нормировании меток
# В пересчете в годовое выражение 1.5%
# У бумаг для которых объявлена оферта волатильность иногда снижается до 3%
LOW_STD = 0.001


class STD(DaysParamsMixin, AbstractFeature):
    """СКО за примерно 1 предыдущий месяцев.

    Волатильность является является известным фактором, объясняющим доходность,
    так называемая low-volatility anomaly.

    За основу взята волатильность за последний месяц, чтобы корректно отражать временные вспышки
    волатильности в отдельных акциях. Оптимальный период выбирается при поиске гиперпараметров.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """СКО за указанное количество предыдущих дней."""
        params = params or self._params
        days = params["days"]
        returns = data.log_total_returns(self._tickers, self._last_date)
        returns = returns.apply(np.exp)
        std = returns.rolling(days).std(ddof=1)
        std = std.stack()
        std.name = self.name
        return std


class Scaler(STD):
    """СКО за примерно 1 год.

    Доходности акций обладают явной гетероскедастичностью и варьируются от одной акции к другой, поэтому
    для получения меток данных с одинаковой волатильностью целесообразно нормировать доходность по
    предыдущей волатильности.

    За основу взята волатильность за последний год, чтобы отражать долгосрочные параметры портфеля,
    так как большинство бумаг остается в портфеле по долгу.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """СКО за указанное количество предыдущих дней."""
        std = super().get(params)
        # noinspection PyTypeChecker
        std[std < LOW_STD] = LOW_STD
        return std
