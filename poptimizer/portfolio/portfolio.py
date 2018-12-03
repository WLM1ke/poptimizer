"""Реализация класса портфеля"""
from typing import Dict, Optional

import pandas as pd

from poptimizer.labels import Labels


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
        self._shares[Labels.CASH] = cash
        self._shares[Labels.PORTFOLIO] = 1
        if value:
            pass  # TODO

    def __str__(self):
        df = pd.concat(
            [
                self.lot_size,
                self.lots,
                self.price,
                self.value,
                self.weight,
                self.volume_factor,
            ],
            axis="columns",
        )
        df.columns = ["LOT_SIZE", "LOTS", "PRICE", "VALUE", "WEIGHT", "VOLUME"]
        return f"\nПОРТФЕЛЬ" f"\n" f"\nДата - {self._date}" f"\n" f"\n{df}"

    @property
    def date(self):
        """Отчетная дата портфеля"""
        return self._date

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
        pass  # TODO

    @property
    def lots(self):
        """Количество лотов

        CASH - в рублях и PORTFOLIO - 1
        """
        return self.shares / self.lot_size

    @property
    def prices(self):
        """Цены позиций

        CASH - 1 и PORTFOLIO - расчетная стоимость
        """
        pass  # TODO

    @property
    def value(self):
        """Стоимость позиций"""
        return self.prices * self.shares

    @property
    def weight(self):
        """Доли позиций

        PORTFOLIO - 1
        """
        value = self.value
        return value / value[Labels.PORTFOLIO]

    @property
    def volume_factor(self):
        """Понижающий коэффициент для акций с малым объемом оборотов

        Ликвидность в первом приближении убывает пропорционально квадрату оборота
        """
        pass  # TODO


if __name__ == "__main__":
    pos_ = dict(AKRN=10, GAZP=3)
    cash_ = 10
    date_ = pd.Timestamp("2018-12-03")
    port = Portfolio(date_, cash_, pos_)
    print(port._shares)
