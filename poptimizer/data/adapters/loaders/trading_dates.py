"""Спецификация таблицы с диапазоном торговых дат."""
import asyncio
from typing import Optional

import aiomoex
import pandas as pd

from poptimizer.data.adapters import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import base


class TradingDatesLoader(logger.LoggerMixin, base.AbstractLoader):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def __init__(self) -> None:
        """Кэшируются данные, чтобы сократить количество обращений к серверу MOEX."""
        super().__init__()
        self._dates_cache: Optional[pd.DataFrame] = None
        self._cache_lock = asyncio.Lock()

    async def get(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        name = self._log_and_validate_group(table_name, base.TRADING_DATES)
        if name != base.TRADING_DATES:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        with self._cache_lock:
            if self._dates_cache is not None:
                self._logger.info(f"Загрузка из кэша {table_name}")
                return self._dates_cache

            session = resources.get_aiohttp_session()
            json = await aiomoex.get_board_dates(session, board="TQBR", market="shares", engine="stock")
            self._dates_cache = pd.DataFrame(json)
            self._logger.info(f"Последняя дата с историей: {json[0]['till']}")

            return self._dates_cache
