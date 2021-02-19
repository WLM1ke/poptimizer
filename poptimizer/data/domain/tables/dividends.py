"""Таблицы с дивидендами."""
from datetime import datetime, timedelta
from typing import ClassVar, Final, NamedTuple, Union

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.adapters.gateways import (  # noqa: WPS235
    bcs,
    close_reestry,
    conomy,
    dividends,
    dohod,
    finrange,
    gateways,
    invest_mint,
    nasdaq,
    smart_lab,
)
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import col, domain

DivEvents = Union[events.TickerTraded, events.UpdateDivCommand]


def _convent_to_rur(div: pd.DataFrame, event: DivEvents) -> pd.DataFrame:
    div = div.sort_index(axis=0)
    div = div.dropna()
    div = div[div[event.ticker] != 0]

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
        div = await self._gateway(event.ticker)
        return _convent_to_rur(div, event)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)

    def _new_events(self, event: DivEvents) -> list[domain.AbstractEvent]:
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
        return await self._gateway()

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Нет проверок."""

    def _new_events(self, event: events.TradingDayEnded) -> list[domain.AbstractEvent]:
        """Не порождает событий."""
        return []


class GateWayDesc(NamedTuple):
    """Описание шлюзов для загрузки дивидендов из внешних источников."""

    name: str
    type_: int
    gw: gateways.DivGateway


class DivExt(base.AbstractTable[events.UpdateDivCommand]):
    """Таблица со сводными данными по дивидендам из внешних источников."""

    group: ClassVar[ports.GroupName] = ports.DIV_EXT
    _gateways: Final[tuple[GateWayDesc]] = (
        GateWayDesc("Dohod", col.ORDINARY, dohod.DohodGateway()),
        GateWayDesc("Dohod", col.PREFERRED, dohod.DohodGateway()),
        GateWayDesc("Conomy", col.ORDINARY, conomy.ConomyGateway()),
        GateWayDesc("Conomy", col.PREFERRED, conomy.ConomyGateway()),
        GateWayDesc("BCS", col.ORDINARY, bcs.BCSGateway()),
        GateWayDesc("BCS", col.PREFERRED, bcs.BCSGateway()),
        GateWayDesc("NASDAQ", col.FOREIGN, nasdaq.NASDAQGateway()),
        GateWayDesc("FinRange", col.ORDINARY, finrange.FinRangeGateway()),
        GateWayDesc("FinRange", col.FOREIGN, finrange.FinRangeGateway()),
        GateWayDesc("Close", col.ORDINARY, close_reestry.CloseGateway()),
        GateWayDesc("Close", col.PREFERRED, close_reestry.CloseGateway()),
        GateWayDesc("InvestMint", col.ORDINARY, invest_mint.InvestMintGateway()),
        GateWayDesc("InvestMint", col.PREFERRED, invest_mint.InvestMintGateway()),
    )

    def _update_cond(self, event: events.UpdateDivCommand) -> bool:
        """Если данные отсутствуют, то их надо загрузить, а так же обновить раз в неделю."""
        if (timestamp := self._timestamp) is None:
            return True

        return datetime.utcnow() - timestamp > timedelta(days=7)

    async def _prepare_df(self, event: events.UpdateDivCommand) -> pd.DataFrame:
        """Загружает данные из всех источников и рассчитывает медиану."""
        dfs = []

        for name, type_, gateway in self._gateways:
            if type_ != event.type_:
                continue

            if (df := await gateway(event.ticker)) is not None:
                df = _convent_to_rur(df, event)
                df.columns = [name]
                dfs.append(df)

        df = pd.DataFrame()
        if dfs:
            df = pd.concat(dfs, axis=1)
            df = df.dropna(thresh=2)
        df["MEDIAN"] = df.median(axis=1)
        return df

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)

    def _new_events(self, event: events.UpdateDivCommand) -> list[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []
