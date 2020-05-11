"""Реализация класса портфеля."""
import functools
from typing import Dict, Optional, Union

import numpy as np
import pandas as pd

from poptimizer import data
from poptimizer.config import POptimizerError, MAX_TRADE

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
        """Понижающий коэффициент для акций с малым объемом оборотов относительно открытой позиции."""
        last_turnover = self._median_turnover(tuple(self.index[:-2]))
        result = (self.value / last_turnover).reindex(self.index)
        result = 1 - result / result.max()
        result[[CASH, PORTFOLIO]] = [1, 1]
        result.name = "TURNOVER"
        return result

    def _median_turnover(self, tickers) -> pd.Series:
        """Медианный оборот за несколько последних дней."""
        last_turnover = data.turnovers(tickers, self.date)
        last_turnover = last_turnover.iloc[-int(1 / MAX_TRADE) :]
        last_turnover = last_turnover.median(axis=0)
        return last_turnover

    def add_tickers(self) -> None:
        """Претенденты для добавления."""
        all_tickers = data.securities_with_reg_number()
        last_turnover = self._median_turnover(tuple(all_tickers))
        # noinspection PyTypeChecker
        last_turnover = last_turnover[last_turnover > 0]
        index = last_turnover.index.difference(self.index)
        last_turnover = last_turnover.reindex(index)
        last_turnover = last_turnover.sort_values(ascending=False).astype("int")
        print(f"\nДЛЯ ДОБАВЛЕНИЯ\n\n{last_turnover}")
