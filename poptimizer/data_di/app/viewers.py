"""Показывает данные из таблиц."""
import asyncio
from typing import Tuple

import pandas as pd

from poptimizer import config
from poptimizer.data_di.domain.tables import base
from poptimizer.shared import adapters, domain


class NoDFError(config.POptimizerError):
    """Данные отсутствуют."""


class Viewer:
    """Показывает данные из таблиц."""

    def __init__(self, mapper: adapters.Mapper[base.AbstractTable[domain.AbstractEvent]]) -> None:
        """Сохраняет ссылку на mapper."""
        self._mapper = mapper
        self._loop = asyncio.get_event_loop()

    def get_df(
        self,
        group: str,
        name: str,
    ) -> pd.DataFrame:
        """Возвращает DataFrame по наименованию."""
        return self._loop.run_until_complete(self._query(group, name))

    def get_dfs(
        self,
        group: str,
        names: Tuple[str, ...],
    ) -> Tuple[pd.DataFrame, ...]:
        """Возвращает несколько DataFrame из одной группы."""
        tasks = [self._query(group, name) for name in names]
        return self._loop.run_until_complete(asyncio.gather(*tasks))

    async def _query(
        self,
        group: str,
        name: str,
    ) -> pd.DataFrame:
        """Выполняет асинхронный запрос."""
        id_ = base.create_id(group, name)
        doc = await self._mapper.get_doc(id_)

        if (df_data := doc.get("data")) is None:
            raise NoDFError(group, name)

        return pd.DataFrame(**df_data)
