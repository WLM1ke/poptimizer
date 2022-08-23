"""Информация о торговых днях."""
import logging
from datetime import datetime

import aiohttp
import aiomoex
import pandas as pd

from poptimizer.data.domain import Group, Table
from poptimizer.data.repo import Repo


class DatesSrv:
    """Таблица с данными о торговых днях.

    Обрабатывает событие начала работы приложения.
    Инициирует событие в случае окончания очередного торгового дня.
    """

    def __init__(self, repo: Repo, session: aiohttp.ClientSession) -> None:
        """Сохраняет необходимые данные и кэширует старое значение."""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._repo = repo
        self._session = session

    async def get(self) -> datetime:
        """Выдает последнюю дату с рыночными данным."""
        table = await self._repo.get(Group.TRADING_DATE)

        return table.timestamp or datetime.fromtimestamp(0)

    async def update(self, checked_day: datetime) -> datetime | None:
        """Обновляет информацию о торговых датах, если они изменились.

        Возвращает последнюю дату с рыночными данным или None при ошибке выполнения.
        """
        if (timestamp := await self._download()) is None:
            return None

        if timestamp <= checked_day:
            return timestamp

        table = Table(
            group=Group.TRADING_DATE,
            name=None,
            timestamp=timestamp,
            df=pd.DataFrame(),
        )

        await self._repo.save(table)

        return timestamp

    async def _download(self) -> datetime | None:
        json = await aiomoex.get_board_dates(
            self._session,
            board="TQBR",
            market="shares",
            engine="stock",
        )

        if (count := len(json)) != 1:
            self._logger.warning(f"wrong rows count {count}")

            return None

        if (date := json[0].get("till")) is None:
            self._logger.warning(f"no till key {json[0]}")

            return None

        return datetime.fromisoformat(date)
