"""Метки для обучения."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin

YEAR_IN_TRADING_DAYS = 12 * 21


class Label(DaysParamsMixin, AbstractFeature):
    """Метка для обучения - средняя доходность за несколько следующих дней.

    Обычно в академических исследованиях ориентируются на ежемесячную доходность,
    однако в ряд признаков имеет более высокую предсказательную способность на других временных
    интервалах. Так большинство метрик, основывающихся на истории цен, имеют максимальную
    предсказательную способность в интервале от 1 до 6 месяцев, а на фундаментальных факторах часто
    максимальная предсказательная способность наблюдается для доходности в следующие несколько лет.
    Оптимальный прогнозный период выбирается при поиске гиперпараметров.

    Согласно исследованиям Шиллера колебание стоимости акций, существенно превосходит колебание
    дивидендов, поэтому для долгосрочного инвестора одним из вариантов является оптимизация,
    не общей доходности, а более предсказуемой и менее изменчивой дивидендной. Данный признак
    позволяет выбрать любую пропорцию между дивидендной и общей доходностью для оптимизации.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)

    def get_params_space(self) -> dict:
        """Выбираемое количество дней для расчета и предустановленная доля дивидендов."""
        space = super().get_params_space()
        space["div_share"] = self._params["div_share"]
        return space

    def get(self, params=None) -> pd.Series:
        """Средняя доходность за указанное количество следующих дней."""
        params = params or self._params
        days = params["days"]
        div_share = params["div_share"]

        returns = data.log_total_returns(self._tickers, self._last_date)
        returns = returns.rolling(days).mean()
        returns = returns.shift(-days)

        div, price = data.div_ex_date_prices(self._tickers, self._last_date)
        div = div.rolling(days).mean()
        div = div.shift(-days)
        div = div / price

        label = returns * (1 - div_share) + div * div_share
        label = label.stack()
        label.name = self.name
        return label
