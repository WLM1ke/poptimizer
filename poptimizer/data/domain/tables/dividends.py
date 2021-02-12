"""Таблицы с дивидендами."""
from datetime import datetime, timedelta
from typing import ClassVar, Final, List, NamedTuple, Tuple, Union

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.adapters.gateways import (
    bcs,
    conomy,
    dividends,
    dohod,
    finrange,
    gateways,
    nasdaq,
    smart_lab,
)
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import col, domain

# Типы шлюзов дивидендов
SHARES = "shares"
FOREIGN_SHARES = "foreignshares"

DivEvents = Union[events.TickerTraded, events.UpdateDivCommand]


def _convent_to_rur(div: pd.DataFrame, event: DivEvents) -> pd.DataFrame:
    div = div.sort_index(axis=0)
    rate = event.usd[col.CLOSE]
    rate = rate.reindex(index=div.index, method="ffill")
    div[col.CURRENCY] = rate.mask(
        div[col.CURRENCY] == col.RUR,
        1,
    )
    div[event.ticker] = div.prod(axis=1)
    div = div.drop(col.CURRENCY, axis=1)
    return div.groupby(lambda date: date).sum()


class Dividends(base.AbstractTable[DivEvents]):
    """Таблица с основной версией дивидендов."""

    group: ClassVar[ports.GroupName] = ports.DIVIDENDS
    _gateway: Final = dividends.DividendsGateway()

    def _update_cond(self, event: DivEvents) -> bool:
        """Если дивиденды отсутствуют и поступила команда обновления, то их надо загрузить."""
        return self._df is None or isinstance(event, events.UpdateDivCommand)

    async def _prepare_df(self, event: DivEvents) -> pd.DataFrame:
        """Загружает новый DataFrame полностью."""
        div = await self._gateway.get(event.ticker)
        return _convent_to_rur(div, event)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)

    def _new_events(self, event: DivEvents) -> List[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []


class SmartLab(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с ожидаемыми дивидендами со https://www.smart-lab.ru.

    Создает события с новыми дивидендами.
    """

    group: ClassVar[ports.GroupName] = ports.SMART_LAB
    _gateway: Final = smart_lab.SmartLabGateway()

    def _update_cond(self, event: events.TradingDayEnded) -> bool:
        """Если торговый день окончился, всегда обновление."""
        return True

    async def _prepare_df(self, event: events.TradingDayEnded) -> pd.DataFrame:
        """Загружает новый DataFrame полностью."""
        return await self._gateway.get()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Нет проверок."""

    def _new_events(self, event: events.TradingDayEnded) -> List[domain.AbstractEvent]:
        """Не порождает событий."""
        return []


class GateWayDesc(NamedTuple):
    """Описание шлюзов для загрузки дивидендов из внешних источников."""

    name: str
    market: str
    gw: gateways.DivGateway


class DivExt(base.AbstractTable[events.UpdateDivCommand]):
    """Таблица со сводными данными по дивидендам из внешних источников."""

    group: ClassVar[ports.GroupName] = ports.DIV_EXT
    _gateways: Final[Tuple[GateWayDesc]] = (
        GateWayDesc("Dohod", SHARES, dohod.DohodGateway()),
        GateWayDesc("Conomy", SHARES, conomy.ConomyGateway()),
        GateWayDesc("BCS", SHARES, bcs.BCSGateway()),
        GateWayDesc("NASDAQ", FOREIGN_SHARES, nasdaq.NASDAQGateway()),
        GateWayDesc("FinRange", SHARES, finrange.FinRangeGateway()),
        GateWayDesc("FinRange", FOREIGN_SHARES, finrange.FinRangeGateway()),
    )

    def _update_cond(self, event: events.UpdateDivCommand) -> bool:
        """Если данные отсутствуют, то их надо загрузить, а так же обновить раз в неделю."""
        if (timestamp := self._timestamp) is None:
            return True

        if datetime.utcnow() - timestamp > timedelta(days=7):
            return True

        return False

    async def _prepare_df(self, event: events.UpdateDivCommand) -> pd.DataFrame:
        """Загружает данные из всех источников и рассчитывает медиану."""
        dfs = []

        for name, market, gateway in self._gateways:
            if market != event.market:
                continue

            df = await gateway.get(event.ticker)
            df = _convent_to_rur(df, event)
            df.columns = [name]
            dfs.append(df)

        df = pd.concat(dfs, axis=1)
        df["MEDIAN"] = df.median(axis=1)
        return df

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)

    def _new_events(self, event: events.UpdateDivCommand) -> List[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []
