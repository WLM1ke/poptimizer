"""Реализация класса портфеля."""
import collections
import functools
import logging
from typing import Optional, Union

import numpy as np
import pandas as pd
import yaml

from poptimizer import config
from poptimizer.data.views import indexes, listing, quotes

VALUE_REL_TOL = 2.0e-4
CASH = "CASH"
PORTFOLIO = "PORTFOLIO"
LIQUIDITY_DAYS = config.YEAR_IN_TRADING_DAYS
LIQUIDITY_DAYS_SHORT = config.MONTH_IN_TRADING_DAYS
SELECT_DAYS = (LIQUIDITY_DAYS + config.FORECAST_DAYS + config.MIN_TEST_DAYS) * 2

LOGGER = logging.getLogger()


class Portfolio:
    """Основные количественные и стоимостные характеристики портфеля.

    Характеристики предоставляются в виде pd.Series с индексом, содержащим все позиции в алфавитном
    порядке, потом CASH и PORTFOLIO.
    """

    def __init__(
        self,
        name: list[str],
        date: Union[str, pd.Timestamp],
        cash: int,
        positions: dict[str, int],
        value: Optional[float] = None,  # noqa: WPS110
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
        :raises POptimizerError:
            Не совпадает в пределах точности расчетная и введенная стоимости портфеля.
        """
        self.name = name
        self._date = pd.Timestamp(date)
        self._shares = pd.Series(positions).sort_index()
        self._shares[CASH] = cash
        self._shares[PORTFOLIO] = 1
        self._shares.name = "SHARES"
        if value is not None:
            if not np.isclose(self.value[PORTFOLIO], value, rtol=VALUE_REL_TOL):
                calc_value = self.value[PORTFOLIO]
                raise config.POptimizerError(
                    f"Введенная стоимость портфеля {value} не равна расчетной {calc_value}",
                )

    def __str__(self) -> str:
        """Отображает сводную информацию о портфеле."""
        name = ", ".join(self.name)
        blocks = [
            f"ПОРТФЕЛЬ [{name}] - {self._date.date()}",
            self._positions_stats(),
            f"{self._main_info_df()}",
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
        df = pd.concat(columns, axis="columns")
        df = df.loc[df["VALUE"] > 0]

        return pd.concat([df.iloc[:-2].sort_values("VALUE", ascending=False), df.iloc[-2:]], axis=0)

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
        lot_size = listing.lot_size(tuple(self.index[:-2]))
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
        price = quotes.prices(tuple(self.index[:-2]), self.date)
        try:
            price = price.iloc[-1]
        except KeyError:
            raise config.POptimizerError(f"Для даты {self._date.date()} отсутствуют исторические " f"котировки")
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
        """Медианный дневной оборот, как доля от портфеля."""
        last_turnover = self._median_turnover(tuple(self.index[:-2]))
        last_turnover = last_turnover / self.value[PORTFOLIO]
        last_turnover[CASH] = last_turnover.sum()
        last_turnover[PORTFOLIO] = last_turnover[CASH]
        last_turnover.name = "TURNOVER"

        return last_turnover.reindex(self.index)

    def _median_turnover(self, tickers) -> pd.Series:
        """Медианный оборот за несколько последних дней."""
        last_turnover = quotes.turnovers(tickers, self.date).iloc[-SELECT_DAYS:].sort_index(ascending=False)

        return last_turnover.expanding().median().iloc[LIQUIDITY_DAYS_SHORT :].min()

    def add_tickers(self) -> None:
        """Претенденты для добавления."""
        all_tickers = listing.securities()
        last_turnover = self._median_turnover(tuple(all_tickers))
        minimal_turnover = self.value[PORTFOLIO] / (len(self.index) - 2)
        last_turnover = last_turnover[last_turnover.gt(minimal_turnover)]

        index = last_turnover.index.difference(self.index)
        if not len(index):
            LOGGER.info(f"\nНЕТ ЛИКВИДНЫХ БУМАГ ДЛЯ ДОБАВЛЕНИЯ")

            return

        last_turnover = last_turnover.reindex(index)
        last_turnover = last_turnover.astype("int")

        rez = last_turnover.sort_values(ascending=False).dropna().astype(int)

        LOGGER.info(f"\nДЛЯ ДОБАВЛЕНИЯ\n\n{rez}")  # noqa: WPS421

    def remove_tickers(self):
        """Претенденты на удаление."""
        tickers = self.index[:-2]
        last_turnover = self._median_turnover(tuple(tickers))
        minimal_turnover = self.value[PORTFOLIO] / (len(self.index) - 2)

        low_turnover = last_turnover[last_turnover.lt(minimal_turnover)]
        low_turnover = low_turnover.sort_values().astype(int)

        if len(low_turnover):
            LOGGER.info(f"\nДЛЯ УДАЛЕНИЯ\n\n{low_turnover}")

            return

        LOGGER.info(f"\nНЕТ НЕЛИКВИДНЫХ БУМАГ ДЛЯ УДАЛЕНИЯ")


def load_from_yaml(date: Union[str, pd.Timestamp], ports: set = None) -> Portfolio:
    """Загружает информацию о портфеле из yaml-файлов."""
    usd = indexes.usd(pd.Timestamp(date))
    usd = usd.iloc[-1]
    cash = 0
    value = 0

    positions = collections.Counter()
    name = list()
    for path in sorted(config.PORT_PATH.glob("*.yaml")):
        if ports is None or path.name in ports:
            name.append(path.stem)
            with path.open() as port:
                port = yaml.safe_load(port)
                positions.update(port.pop("positions"))
                cash += port.get("USD", 0) * usd + port.get("RUR", 0)
                value += port.get("value", 0)

            if value:
                LOGGER.info(f"Проверка стоимости: {path}")
                try:
                    Portfolio([path.stem], date, cash, positions, value)
                except config.POptimizerError as err:
                    LOGGER.error(err)
                    continue
                LOGGER.info("OK")

    if not value:
        value = None

    return Portfolio(name, date, cash, positions, value)


def load_tickers() -> tuple[str]:
    """Отсортированный перечень используемых тикеров."""
    all_pos = set()
    for path in config.PORT_PATH.glob("*.yaml"):
        with path.open() as port:
            port = yaml.safe_load(port)
            pos = port.pop("positions")
            all_pos.update(pos)

    return tuple(sorted(all_pos))
