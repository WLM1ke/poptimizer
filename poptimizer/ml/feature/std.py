"""Признак - СКО за последние торговые дни."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin

# Обрезка совсем маленьких значений, чтобы не было переполнения при нормировании меток
LOW_STD = 0.001


class STD(DaysParamsMixin, AbstractFeature):
    """СКО за примерно 1 предыдущий месяцев.

    СКО выступает в двоякой роли. С одной стороны, доходности акций обладают явной
    гетероскедастичностью и варьируются от одной акции к другой, поэтому для получения меток данных  с
    одинаковой волатильностью целесообразно нормировать доходность по предыдущей волатильности. С
    другой стороны, сама волатильность является является известным фактором, объясняющим доходность,
    так называемая low-volatility anomaly.

    За основу взята волатильность за последний месяц, чтобы корректно отражать временные вспышки
    волатильности в отдельных акциях. Оптимальный период выбирается при поиске гиперпараметров.
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """СКО за указанное количество предыдущих дней."""
        params = params or self._params
        days = params["days"]
        returns = data.log_total_returns(self._tickers, self._last_date)
        std = returns.rolling(days).std()
        std = std.stack()
        std.name = self.name
        return std[std > LOW_STD]
