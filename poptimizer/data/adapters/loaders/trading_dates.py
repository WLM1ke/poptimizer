"""Загрузка таблицы с диапазоном торговых дат."""
import asyncio
from typing import Optional

import aiomoex
import pandas as pd

from poptimizer.data.adapters import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import outer


class TradingDatesLoader(logger.LoaderLoggerMixin, outer.AbstractLoader):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def __init__(self) -> None:
        """Кэшируются данные, чтобы сократить количество обращений к серверу MOEX."""
        super().__init__()
        self._dates_cache: Optional[pd.DataFrame] = None
        self._cache_lock = asyncio.Lock()

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        name = self._log_and_validate_group(table_name, outer.TRADING_DATES)
        if name != outer.TRADING_DATES:
            raise outer.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        async with self._cache_lock:
            if self._dates_cache is not None:
                self._logger.log(f"Загрузка из кэша {table_name}")
                return self._dates_cache

            session = resources.get_aiohttp_session()
            json = await aiomoex.get_board_dates(session, board="TQBR", market="shares", engine="stock")
            self._dates_cache = pd.DataFrame(json, dtype="datetime64[ns]")
            self._logger.log(f"Последняя дата с историей: {json[0]['till']}")

            return self._dates_cache
