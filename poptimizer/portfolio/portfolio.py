"""Реализация класса портфеля."""
import collections
import functools
from typing import Dict, Optional, Union, NoReturn

import numpy as np
import pandas as pd
import yaml

from poptimizer import config
from poptimizer.config import POptimizerError, MAX_TRADE
from poptimizer.data.views import moex
from poptimizer.dl.features import data_params
from poptimizer.store import database

CASH = "CASH"
PORTFOLIO = "PORTFOLIO"
MAX_HISTORY = database.MONGO_CLIENT["data"]["models"].find_one(
    {},
    projection={"_id": False, "genotype.Data.history_days": True},
    sort=[("genotype.Data.history_days", -1)],
)
try:
    MAX_HISTORY = int(MAX_HISTORY["genotype"]["Data"]["history_days"])
    ADD_DAYS = (MAX_HISTORY + data_params.FORECAST_DAYS * 2) * 2
except TypeError:
    MAX_HISTORY = int(1 / config.MAX_TRADE)
    ADD_DAYS = int(1 / config.MAX_TRADE)


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
        self._shares = pd.Series(positions).sort_index()
        self._shares[CASH] = cash
        self._shares[PORTFOLIO] = 1
        self._shares.name = "SHARES"
        if value is not None and not np.isclose(self.value[PORTFOLIO], value, rtol=2.0e-4):
            raise POptimizerError(
                f"Введенная стоимость портфеля {value} " f"не равна расчетной {self.value[PORTFOLIO]}"
            )

    def __str__(self) -> str:
        blocks = [
            f"ПОРТФЕЛЬ - {self._date.date()}",
            self._positions_stats(),
            f"{self._main_info_df()}",
            self._least_liquid_pos(),
        ]
        return "\n\n".join(blocks)

    def _main_info_df(self) -> pd.DataFrame:
        """Сводная информация по портфелю."""
        columns = [
            self.lot_size,
            self.shares,
            self.price,
            self.value,
            self.weight,
            self.turnover_factor,
        ]
        return pd.concat(columns, axis="columns")

    def _positions_stats(self) -> str:
        """Информация о количестве позиций"""
        weights = self.weight.iloc[:-2]
        blocks = [
            f"Количество бумаг - {len(weights)}",
            f"Открытых позиций - {(weights > 0).sum()}",
        ]
        if (sum_w := self.weight.iloc[:-2].sum()) != 0:
            weights = weights / sum_w
            blocks.append(f"Эффективных позиций - {int(1 / (weights ** 2).sum())}")
        return "\n".join(blocks)

    def _least_liquid_pos(self) -> str:
        """Наименее ликвидная позиция по соотношению размера и дневного оборота."""
        result = self.value / self._median_turnover(tuple(self.index[:-2]), MAX_HISTORY)
        return f"НАИМЕНЕЕ ЛИКВИДНАЯ ПОЗИЦИЯ:\n{result.idxmax()} - {result.max():.0%}"

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
        lot_size = moex.lot_size(tuple(self.index[:-2]))
        lot_size = lot_size.reindex(self.index, fill_value=1)
        lot_size.name = "LOT_SIZE"
        return lot_size

    @property
    def lots(self) -> pd.Series:
        """Количество лотов.

        CASH - в рублях и PORTFOLIO - 1.
        """
        lots = self.shares / self.lot_size
        lots.name = "LOTS"
        return lots

    @property
    @functools.lru_cache(maxsize=1)
    def price(self) -> pd.Series:
        """Цены позиций.

        CASH - 1 и PORTFOLIO - расчетная стоимость.
        """
        price = moex.prices(tuple(self.index[:-2]), self.date)
        try:
            price = price.loc[self.date]
        except KeyError:
            raise POptimizerError(f"Для даты {self._date.date()} отсутствуют исторические котировки")
        price[CASH] = 1
        price[PORTFOLIO] = (self.shares[:-1] * price).sum(axis=0)
        price.name = "PRICE"
        return price

    @property
    def value(self) -> pd.Series:
        """Стоимость позиций."""
        value = self.price * self.shares
        value.name = "VALUE"
        return value

    @property
    def weight(self) -> pd.Series:
        """Доли позиций.

        PORTFOLIO - 1.
        """
        value = self.value
        weight = value / value[PORTFOLIO]
        weight.name = "WEIGHT"
        return weight

    @property
    def turnover_factor(self) -> pd.Series:
        """Понижающий коэффициент для акций с малым объемом оборотов относительно открытой позиции."""
        last_turnover = self._median_turnover(tuple(self.index[:-2]), MAX_HISTORY)
        result = (self.value / last_turnover).reindex(self.index)
        last_turnover = last_turnover * result.max() - self.value
        result = last_turnover / (self.value[PORTFOLIO] * MAX_TRADE)
        result[result < 0] = 0
        max_factor = result.sum()
        result[CASH] = max_factor
        result[PORTFOLIO] = max_factor
        result.name = "TURNOVER"
        return result

    def _median_turnover(self, tickers, days) -> pd.Series:
        """Медианный оборот за несколько последних дней."""
        last_turnover = moex.turnovers(tickers, self.date)
        last_turnover = last_turnover.iloc[-days:]
        last_turnover = last_turnover.median(axis=0)
        return last_turnover

    def add_tickers(self) -> NoReturn:
        """Претенденты для добавления."""
        all_tickers = moex.securities()
        last_turnover = self._median_turnover(tuple(all_tickers), ADD_DAYS)
        minimal_turnover = self.value[PORTFOLIO] * MAX_TRADE
        last_turnover = last_turnover[last_turnover.gt(minimal_turnover)]

        index = last_turnover.index.difference(self.index)
        last_turnover = last_turnover.reindex(index)
        last_turnover = last_turnover.sort_values(ascending=False).astype("int")

        returns_new = self.norm_ret(tuple(index))
        returns_old = self.norm_ret(tuple(self.index[:-2]))
        corr_max = (returns_new.T @ returns_old / MAX_HISTORY).max(axis=1).sort_values()

        print(f"\nДЛЯ ДОБАВЛЕНИЯ\n\n{last_turnover}\n{corr_max}")

    def norm_ret(self, tickers):
        div, p1 = moex.div_and_prices(tickers, self.date)
        p0 = p1.shift(1)
        returns_new = (p1 + div) / p0
        returns_new = returns_new.iloc[-MAX_HISTORY:]
        returns_new = (returns_new - returns_new.mean(axis=0)) / returns_new.std(axis=0, ddof=0)
        return returns_new


def load_from_yaml(date: Union[str, pd.Timestamp]) -> Portfolio:
    """Загружает информацию о портфеле из yaml-файлов."""
    positions = collections.Counter()
    kwargs = collections.Counter()
    for path in config.PORT_PATH.glob("*.yaml"):
        with path.open() as file:
            doc = yaml.safe_load(file)
            pos = doc.pop("positions")
            positions.update(pos)
            kwargs.update(doc)
    kwargs["positions"] = positions
    kwargs["date"] = date
    return Portfolio(**kwargs)
