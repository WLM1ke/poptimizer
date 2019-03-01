"""Признак - дивиденды за последние периоды."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.config import DIVYIELD_RANGE
from poptimizer.ml.feature.feature_old import AbstractFeature, DaysParamsMixin
from poptimizer.store import DIVIDENDS_START


class DivYield(DaysParamsMixin, AbstractFeature):
    """Dividend to price - дивидендная доходность примерно за 12 предыдущих месяцев.

    Акции с высокими дивидендами относительно цены во многих исследованиях показываются
    более высокую доходность - value anomaly. Большинство исследований отмечают более значительное
    влияние этого фактора на долгосрочную доходность - корреляция между дивидендной доходностью
    последующей доходностью акции близка к нулю для месячной доходности и непрерывно увеличивается на
    горизонтах вплоть до 5 лет, достигая очень высоких значений. Так же часто отмечается нелинейный
    характер зависимости - влияние более существенно для акций с низкой и умеренной дивидендной
    доходностью и ослабевает для акций с очень высокой дивидендной доходностью.

    Так как даты отсечек немного плывут во времени, обычно целесообразно использовать интервал времени
    немного отличающийся от 12 месяцев, чтобы исключить влияние этого фактора. Оптимальный период
    расчета дивидендов выбирается во время поиска гиперпараметров.
    """

    RANGE = DIVYIELD_RANGE

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp):
        super().__init__(tickers, last_date)
        self._dividends = data.dividends(tickers, last_date)
        self._prices = data.prices(tickers, last_date)

    def get(self, date: pd.Timestamp, **kwargs) -> pd.Series:
        """Дивидендная доходность за несколько предыдущих дней."""
        prices = self._prices
        loc = prices.index.get_loc(date)
        days = kwargs["days"]
        start = prices.index[loc - days + 1]
        if start >= DIVIDENDS_START:
            last_prices = prices.loc[date]
            dividends = self._dividends.loc[start:date].sum(axis=0)
            yields = dividends / last_prices
            yields.name = self.name
            return yields
        return pd.Series(index=list(self._tickers), name=self.name)
