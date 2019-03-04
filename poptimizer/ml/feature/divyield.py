"""Признак - дивиденды за последний год."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin
from poptimizer.store import DIVIDENDS_START


# noinspection PyUnresolvedReferences
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

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)
        self._dividends, self._prices = data.div_ex_date_prices(tickers, last_date)

    def get(self, params=None) -> pd.Series:
        """Дивидендная доходность за несколько предыдущих дней."""
        params = params or self._params
        days = params["days"]
        div = self._dividends.rolling(days).sum().loc[DIVIDENDS_START:].iloc[days:]
        div = div / self._prices
        div = div.stack()
        div.name = self.name
        return div
