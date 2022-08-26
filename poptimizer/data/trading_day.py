"""Информация о торговых днях."""
from datetime import datetime

import aiohttp
import aiomoex

from poptimizer.data import domain
from poptimizer.data.repo import Repo


class DatesSrv:
    """Таблица с данными о торговых днях.

    Обрабатывает событие начала работы приложения.
    Инициирует событие в случае окончания очередного торгового дня.
    """

    def __init__(self, repo: Repo, session: aiohttp.ClientSession) -> None:
        self._repo = repo
        self._session = session

    async def get_last_date(self) -> datetime:
        """Выдает последнюю дату с рыночными данным."""
        table = await self._repo.get(domain.Group.TRADING_DATE)

        return table.timestamp or datetime.fromtimestamp(0)

    async def update(self, checked_day: datetime) -> datetime:
        """Обновляет информацию о торговых датах, если они изменились.

        Возвращает последнюю дату с рыночными данным.
        """
        timestamp = await self._download()

        if timestamp > checked_day:
            await self._save(timestamp)

        return timestamp

    async def _download(self) -> datetime:
        json = await aiomoex.get_board_dates(
            self._session,
            board="TQBR",
            market="shares",
            engine="stock",
        )

        if (count := len(json)) != 1:
            raise domain.DataError(f"wrong rows count {count}")

        if (date := json[0].get("till")) is None:
            raise domain.DataError(f"no till key {json[0]}")

        return datetime.fromisoformat(date)

    async def _save(self, timestamp: datetime) -> None:
        table = domain.Table(
            group=domain.Group.TRADING_DATE,
            timestamp=timestamp,
        )

        return await self._repo.save(table)
