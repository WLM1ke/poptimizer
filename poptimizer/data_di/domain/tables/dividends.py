"""Таблицы с дивидендами."""
import types
from datetime import datetime, timedelta
from typing import ClassVar, Final, List, Mapping, Union

import pandas as pd

from poptimizer.data_di.adapters.gateways import bcs, gateways, conomy, dividends, dohod, smart_lab
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base, checks
from poptimizer.shared import domain
from poptimizer.shared import col

DivEvents = Union[events.TickerTraded, events.UpdateDivCommand]


class Dividends(base.AbstractTable[DivEvents]):
    """Таблица с основной версией дивидендов."""

    group: ClassVar[base.GroupName] = base.DIVIDENDS
    _gateway: Final = dividends.DividendsGateway()

    def _update_cond(self, event: DivEvents) -> bool:
        """Если дивиденды отсутствуют, то их надо загрузить."""
        return self._df is None or isinstance(event, events.UpdateDivCommand)

    async def _prepare_df(self, event: DivEvents) -> pd.DataFrame:
        """Загружает новый DataFrame полностью."""
        return await self._gateway.get(event.ticker)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        checks.unique_increasing_index(df_new)

    def _new_events(self, event: DivEvents) -> List[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []


class SmartLab(base.AbstractTable[events.TradingDayEnded]):
    """Таблица с ожидаемыми дивидендами со https://www.smart-lab.ru.

    Создает события с новыми дивидендами.
    """

    group: ClassVar[base.GroupName] = base.SMART_LAB
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
        """Создает события о новых дивидендах."""
        if (df := self._df) is None:
            raise base.TableNeverUpdatedError(self._id)

        div_tickers = set(df.index)
        new_events: List[domain.AbstractEvent] = []

        for ticker in div_tickers:
            df_div = df[df.index == ticker]
            df_div = df_div.set_index(col.DATE)
            df_div = df_div[[col.DIVIDENDS]]
            df_div.columns = ["SmartLab"]
            new_events.append(events.DivExpected(ticker, df_div))

        return new_events


class DivExt(base.AbstractTable[events.DivExpected]):
    """Таблица со сводными данными по дивидендам из внешних источников."""

    group: ClassVar[base.GroupName] = base.DIV_EXT
    _gateways_dict: Final[Mapping[str, gateways.DivGateway]] = types.MappingProxyType(
        {
            "Dohod": dohod.DohodGateway(),
            "Conomy": conomy.ConomyGateway(),
            "BCS": bcs.BCSGateway(),
        },
    )

    def _update_cond(self, event: events.DivExpected) -> bool:
        """Если данные отсутствуют, то их надо загрузить, а так же обновить раз в неделю."""
        if (timestamp := self._timestamp) is None:
            return self._df is None

        if datetime.utcnow() - timestamp > timedelta(days=7):
            return True

        return False

    async def _prepare_df(self, event: events.DivExpected) -> pd.DataFrame:
        """Загружает данные из всех источников и рассчитывает медиану."""
        dfs = [event.df]
        for name, gateway in self._gateways_dict.items():
            df = await gateway.get(event.ticker)
            df.columns = [name]
            dfs.append(df)

        df = pd.concat(dfs, axis=1)
        df["MEDIAN"] = df.median(axis=1)
        return df

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        checks.unique_increasing_index(df_new)

    def _new_events(self, event: events.DivExpected) -> List[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []
