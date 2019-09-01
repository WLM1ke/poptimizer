"""Признак - день в году."""
from typing import Tuple, List

import pandas as pd
from hyperopt import hp

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, ON_OFF


class DayOfYear(AbstractFeature):
    """День в году.

    Многие исследования выделяют различные календарные факторы в доходности активов. Выплата
    дивидендов так же крайне неравномерно распределена в течении года.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    @staticmethod
    def is_categorical(params) -> List[bool]:
        """Категориальный признак."""
        return [False]

    def get_params_space(self) -> dict:
        """Специальных параметров нет, но поддерживается возможность отключения."""
        return {ON_OFF: hp.choice(f"{self.name}_ON_OFF", [True, False])}

    def get(self, params=None) -> pd.Series:
        """Для дат, в которые есть котировки указывается номер года."""
        returns = data.log_total_returns(self._tickers, self._last_date)
        tickers = returns.stack()
        tickers.loc[:] = tickers.index.get_level_values(0).dayofyear
        tickers.name = self.name
        return tickers
