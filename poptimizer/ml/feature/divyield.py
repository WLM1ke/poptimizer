"""Признак - дивиденды за последний год."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysPeriodsParamsMixin


class DivYield(DaysPeriodsParamsMixin, AbstractFeature):
    """Dividend to price - дивидендная доходность примерно за 12 предыдущих месяцев.

    Акции с высокими дивидендами относительно цены во многих исследованиях показываются
    более высокую доходность - value anomaly. Большинство исследований отмечают более значительное
    влияние этого фактора на долгосрочную доходность - корреляция между дивидендной доходностью
    последующей доходностью акции близка к нулю для месячной доходности и непрерывно увеличивается на
    горизонтах вплоть до 5 лет, достигая очень высоких значений. Так же часто отмечается нелинейный
    характер зависимости - влияние более существенно для акций с низкой и умеренной дивидендной
    доходностью и ослабевает для акций с очень высокой дивидендной доходностью. В ряде исследований
    указывается, что большое влияние имеет устойчивость выплаты дивидендов во времени, а краткосрочные
    вспышки величины дивидендов не увеличивают доходность акций.

    Так как даты отсечек плывут во времени, обычно целесообразно использовать интервал времени
    немного отличающийся от 12 месяцев, чтобы исключить влияние этого фактора. Оптимальный период
    расчета дивидендов выбирается во время поиска гиперпараметров. Весь период разбивается на
    подпериоды, что позволяет модели выявлять фактор устойчивости выплат.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get(self, params=None) -> pd.Series:
        """Дивидендная доходность за несколько предыдущих дней."""
        params = params or self._params
        periods = params["periods"]
        days = params["days"] // periods
        dividends, prices = data.div_ex_date_prices(self._tickers, self._last_date)
        div = dividends.rolling(days).sum()
        div_periods = []
        for i in range(periods):
            div_i = div.shift(i * days) / prices
            div_i = div_i.stack()
            div_i.name = f"{self.name}_{i}"
            div_periods.append(div_i)
        return pd.concat(div_periods, axis=1)
