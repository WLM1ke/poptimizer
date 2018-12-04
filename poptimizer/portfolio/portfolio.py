"""Реализация класса портфеля"""
from typing import Dict, Optional

import numpy as np
import pandas as pd

from poptimizer import POptimizerError, CASH, PORTFOLIO
from poptimizer.config import TURNOVER_CUT_OFF, TURNOVER_PERIOD
from poptimizer.data import moex


class Portfolio:
    """Основные количественные и стоймостные характеристики портфеля

    Характеристики предоставляются в виде pd.Series с индексом, содержащим все позиции в алфавитном порядке, потом CASH
    и PORTFOLIO
    """

    def __init__(
        self,
        date: pd.Timestamp,
        cash: int,
        positions: Dict[str, int],
        value: Optional[float] = None,
    ):
        """При создании может быть очуществлена проверка совпадения расчтеной стоимости и введенной

        :param date:
            Дата на которую расчитываются параметры портфеля
        :param cash:
            Количество наличных в портфеле
        :param positions:
            Словарь с тикерами и количеством акций
        :param value:
            Стоимость портфеля на отчетную дату
        """
        self._date = date
        self._shares = pd.Series(positions)
        self._shares.sort_index(inplace=True)
        self._shares[CASH] = cash
        self._shares[PORTFOLIO] = 1
        if not np.isclose(self.value[PORTFOLIO], value):
            raise POptimizerError(
                f"Введенная стоимость портфеля {value} "
                f"не равна расчетной {self.value[PORTFOLIO]}"
            )

    def __str__(self):
        df = pd.concat(
            [
                self.lot_size,
                self.shares,
                self.price,
                self.value,
                self.weights,
                self.turnover_factor,
            ],
            axis="columns",
        )
        df.columns = ["LOT_SIZE", "SHARES", "PRICE", "VALUE", "WEIGHT", "VOLUME"]
        return f"\nПОРТФЕЛЬ\n\nДата - {self._date}\n\n{df}"

    @property
    def date(self):
        """Отчетная дата портфеля"""
        return self._date

    @property
    def index(self):
        """Общий индекс всех характеристик портфеля - перечень позиций, включая CASH и PORTFOLIO"""
        return self.shares.index

    @property
    def shares(self):
        """Количество акций в портфеле,

        CASH - в рублях и PORTFOLIO - 1"""
        return self._shares

    @property
    def lot_size(self):
        """Размер лотов

        CASH и PORTFOLIO - 1
        """
        lot_size = moex.lot_size(tuple(self.index[:-2]))
        return lot_size.reindex(self.index, fill_value=1)

    @property
    def lots(self):
        """Количество лотов

        CASH - в рублях и PORTFOLIO - 1
        """
        return self.shares / self.lot_size

    @property
    def price(self):
        """Цены позиций

        CASH - 1 и PORTFOLIO - расчетная стоимость
        """
        price = moex.prices(self.date, tuple(self.index[:-2]))
        price = price.loc[self.date]
        price[CASH] = 1
        price[PORTFOLIO] = (self.shares[:-1] * price).sum(axis=0)
        return price

    @property
    def value(self):
        """Стоимость позиций"""
        return self.price * self.shares

    @property
    def weights(self):
        """Доли позиций

        PORTFOLIO - 1
        """
        value = self.value
        return value / value[PORTFOLIO]

    @property
    def turnover_factor(self):
        """Понижающий коэффициент для акций с малым объемом оборотов

        Ликвидность в первом приближении убывает пропорционально квадрату оборота
        """
        last_turnover = moex.turnovers(self.date, tuple(self.index[:-2]))
        last_turnover = last_turnover.iloc[-TURNOVER_PERIOD:]
        last_turnover = last_turnover.sum(axis=0)
        turnover_share_of_portfolio = last_turnover / self.value[PORTFOLIO]
        turnover_factor = 1 - (TURNOVER_CUT_OFF / turnover_share_of_portfolio) ** 2
        turnover_factor[turnover_factor < 0] = 0
        return turnover_factor.reindex(self.index, fill_value=1)


if __name__ == "__main__":
    pos_ = dict(AKRN=10, GAZP=3)
    cash_ = 10
    date_ = pd.Timestamp("2018-12-03")
    port = Portfolio(date_, cash_, pos_)
    print(port._shares)
