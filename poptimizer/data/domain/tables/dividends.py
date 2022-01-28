"""Таблицы с дивидендами."""
from datetime import datetime, timedelta
from typing import ClassVar, Final, NamedTuple, Union, cast

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
    moex_status,
    nasdaq,
    smart_lab,
    street_insider,
)
from poptimizer.data.domain import events
from poptimizer.data.domain.tables import base
from poptimizer.shared import col, domain

DivEvents = Union[events.TickerTraded, events.UpdateDivCommand]


def _convent_to_rur(div: pd.DataFrame, event: DivEvents) -> pd.DataFrame:
    div = div.sort_index(axis=0)
    div = div.dropna()
    div = div[div[event.ticker] != 0]

    rate = cast(pd.DataFrame, event.usd)[col.CLOSE]
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
        return True

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


class DivNew(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с ожидаемыми дивидендами.

     Данные забираются со https://www.smart-lab.ru по российским акциям и с https://www.moex.com/ по
     иностранным.

    Создает события с новыми дивидендами.
    """

    group: ClassVar[ports.GroupName] = ports.DIV_NEW
    _gateways: Final = (
        smart_lab.SmartLabGateway(),
        moex_status.MOEXStatusGateway(),
    )

    def _update_cond(self, event: events.TradingDayEnded) -> bool:
        """Если торговый день окончился, всегда обновление."""
        return True

    async def _prepare_df(self, event: events.TradingDayEnded) -> pd.DataFrame:
        """Загружает новый DataFrame полностью."""
        dfs = [await gw() for gw in self._gateways]
        return pd.concat(dfs, axis=0)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Нет проверок."""

    def _new_events(self, event: events.TradingDayEnded) -> list[domain.AbstractEvent]:
        """Порождает команды обновить дивиденды."""
        return []


class GateWayDesc(NamedTuple):
    """Описание шлюзов для загрузки дивидендов из внешних источников."""

    name: str
    type_: int
    gw: gateways.DivGateway


class DivExt(base.AbstractTable[events.UpdateDivCommand]):
    """Таблица со сводными данными по дивидендам из внешних источников."""

    group: ClassVar[ports.GroupName] = ports.DIV_EXT
    _gateways: Final[tuple[GateWayDesc, ...]] = (
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
        GateWayDesc("InvestMint", col.FOREIGN, invest_mint.InvestMintGateway()),
        GateWayDesc("StreetInsider", col.FOREIGN, street_insider.StreetInsider()),
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
        df["MEDIAN"] = df.median(axis=1)
        return df

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        base.check_unique_increasing_index(df_new)

    def _new_events(self, event: events.UpdateDivCommand) -> list[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []
