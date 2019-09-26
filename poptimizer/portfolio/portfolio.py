"""Реализация класса портфеля."""
import functools
from typing import Dict, Optional, Union

import numpy as np
import pandas as pd

from poptimizer import data, config
from poptimizer.config import POptimizerError

CASH = "CASH"
PORTFOLIO = "PORTFOLIO"


class Portfolio:
    """Основные количественные и стоимостные характеристики портфеля.

    Характеристики предоставляются в виде pd.Series с индексом, содержащим все позиции в алфавитном
    порядке, потом CASH и PORTFOLIO.
    """

    def __init__(
        self,
        date: Union[str, pd.Timestamp],
        cash: int,
        positions: Dict[str, int],
        value: Optional[float] = None,
    ):
        """При создании может быть осуществлена проверка совпадения расчетной стоимости и введенной.

        :param date:
            Дата на которую рассчитываются параметры портфеля.
        :param cash:
            Количество наличных в портфеле.
        :param positions:
            Словарь с тикерами и количеством акций.
        :param value:
            Стоимость портфеля на отчетную дату.
        """
        self._date = pd.Timestamp(date)
        self._shares = pd.Series(positions)
        self._shares.sort_index(inplace=True)
        self._shares[CASH] = cash
        self._shares[PORTFOLIO] = 1
        if value is not None and not np.isclose(self.value[PORTFOLIO], value):
            raise POptimizerError(
                f"Введенная стоимость портфеля {value} "
                f"не равна расчетной {self.value[PORTFOLIO]}"
            )

    def __str__(self) -> str:
        df = pd.concat(
            [
                self.lot_size,
                self.shares,
                self.price,
                self.value,
                self.weight,
                self.turnover_factor,
            ],
            axis="columns",
        )
        df.columns = ["LOT_SIZE", "SHARES", "PRICE", "VALUE", "WEIGHT", "VOLUME"]
        return (
            f"\nПОРТФЕЛЬ"
            f"\n"
            f"\nДата - {self._date.date()}"
            f"\nКоличество бумаг - {len(self.index) - 2}"
            f"\n"
            f"\n{df}"
        )

    @property
    def date(self) -> pd.Timestamp:
        """Отчетная дата портфеля."""
        return self._date

    @property
    def index(self) -> pd.Index:
        """Общий индекс всех характеристик портфеля - перечень позиций, включая CASH и PORTFOLIO."""
        return self.shares.index

    @property
    def shares(self) -> pd.Series:
        """Количество акций в портфеле.

        CASH - в рублях и PORTFOLIO - 1."""
        return self._shares

    @property
    def lot_size(self) -> pd.Series:
        """Размер лотов.

        CASH и PORTFOLIO - 1.
        """
        lot_size = data.lot_size(tuple(self.index[:-2]))
        return lot_size.reindex(self.index, fill_value=1)

    @property
    def lots(self) -> pd.Series:
        """Количество лотов.

        CASH - в рублях и PORTFOLIO - 1.
        """
        return self.shares / self.lot_size

    @property
    @functools.lru_cache(maxsize=1)
    def price(self) -> pd.Series:
        """Цены позиций.

        CASH - 1 и PORTFOLIO - расчетная стоимость.
        """
        price = data.prices(tuple(self.index[:-2]), self.date)
        try:
            price = price.loc[self.date]
        except KeyError:
            raise POptimizerError(
                f"Для даты {self._date.date()} отсутствуют исторические котировки"
            )
        price[CASH] = 1
        price[PORTFOLIO] = (self.shares[:-1] * price).sum(axis=0)
        return price

    @property
    def value(self) -> pd.Series:
        """Стоимость позиций."""
        return self.price * self.shares

    @property
    def weight(self) -> pd.Series:
        """Доли позиций.

        PORTFOLIO - 1.
        """
        value = self.value
        return value / value[PORTFOLIO]

    @property
    @functools.lru_cache(maxsize=1)
    def turnover_factor(self) -> pd.Series:
        """Понижающий коэффициент для акций с малым объемом оборотов.

        Ликвидность в первом приближении убывает пропорционально квадрату оборота.
        """
        last_turnover = data.turnovers(tuple(self.index[:-2]), self.date)
        turn_over_factor = config.TURNOVER_FACTOR
        last_turnover = last_turnover.iloc[-turn_over_factor:]
        median_turnover = last_turnover.median(axis=0)
        turnover_share_of_portfolio = median_turnover / self.value[PORTFOLIO]
        turnover_factor = 1 - (1 / turnover_share_of_portfolio / turn_over_factor) ** 2
        turnover_factor[turnover_factor < 0] = 0
        return turnover_factor.reindex(self.index, fill_value=1)
