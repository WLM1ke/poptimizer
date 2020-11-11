"""Таблицы с дивидендами."""
from typing import ClassVar, List

import pandas as pd

from poptimizer.data_di.adapters.gateways import conomy, dividends
from poptimizer.data_di.domain import events
from poptimizer.data_di.domain.tables import base, checks
from poptimizer.data_di.shared import domain


class Dividends(base.AbstractTable[events.DividendsObsoleted]):
    """Таблица с основной версией дивидендов."""

    group: ClassVar[base.GroupName] = base.DIVIDENDS
    _gateway: ClassVar = dividends.DividendsGateway()

    def _update_cond(self, event: events.DividendsObsoleted) -> bool:
        """Если дивиденды устарели, требуется обязательное обновление."""
        return True

    async def _prepare_df(self, event: events.DividendsObsoleted) -> pd.DataFrame:
        """Загружает новый DataFrame полностью."""
        return await self._gateway.get(event.ticker)

    def _validate_new_df(self, df_new: pd.DataFrame) -> None:
        """Индекс должен быть уникальным и возрастающим."""
        checks.unique_increasing_index(df_new)

    def _new_events(self, event: events.DividendsObsoleted) -> List[domain.AbstractEvent]:
        """Обновление дивидендов не порождает события."""
        return []


class Conomy(Dividends):
    """Дивиденды с сайта conomy.ru."""

    group: ClassVar[base.GroupName] = base.CONOMY
    _gateway: ClassVar = conomy.ConomyGateway()
