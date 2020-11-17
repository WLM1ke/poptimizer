"""Показывает данные из таблиц."""
import asyncio
from typing import Tuple

import pandas as pd
from motor import motor_asyncio

from poptimizer import config
from poptimizer.data_di.shared import adapters


class NoDFError(config.POptimizerError):
    """Данные отсутствуют."""


class Viewer:
    """Показывает данные из таблиц."""

    def __init__(self, db: motor_asyncio.AsyncIOMotorDatabase):
        """Сохраняет ссылку на базу в MongoDB."""
        self._db = db
        self._loop = asyncio.get_event_loop()

    def get_df(
        self,
        group: str,
        name: str,
    ) -> pd.DataFrame:
        """Возвращает DataFrame по наименованию."""
        if group == name:
            group = adapters.MISC
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
        doc = await self._db[group].find_one(filter={"_id": name})
        if doc is None:
            raise NoDFError(group, name)

        return pd.DataFrame(**doc["data"])
