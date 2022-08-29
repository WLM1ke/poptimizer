"""Информация о торговых днях."""
from datetime import datetime
from typing import ClassVar

import aiohttp
import aiomoex
from pydantic import BaseModel, Field, ValidationError, validator

from poptimizer.data import domain, exceptions
from poptimizer.data.repo import Repo


class _DatesRow(domain.Row):
    """Строка с данными о торговых днях - должна быть одна."""

    date: datetime = Field(alias="till")


class _Payload(BaseModel):
    df: list[_DatesRow]

    def last_date(self) -> datetime:
        """Возвращает последнюю дату торгов."""
        return self.df[0].date

    @validator("df")
    def _must_be_one_row(cls, df: list[_DatesRow]) -> list[_DatesRow]:
        if (count := len(df)) != 1:
            raise ValueError(f"wrong rows count {count}")

        return df


class DatesTable(BaseModel):
    """Таблица с информацией о последней торговой дате."""

    group: ClassVar[domain.Group] = domain.Group.TRADING_DATE
    id_: str | None = Field(default=None, alias="_id", exclude=True)
    timestamp: datetime = datetime.fromtimestamp(0)


class DatesSrv:
    """Сервис обновления таблицы с данными о торговых днях."""

    def __init__(self, repo: Repo, session: aiohttp.ClientSession) -> None:
        self._repo = repo
        self._session = session

    async def get_last_date(self) -> datetime:
        """Выдает последнюю дату с рыночными данным."""
        table = await self._repo.get(DatesTable)

        return table.timestamp

    async def update(self, checked_day: datetime) -> datetime:
        """Обновляет информацию о торговых датах, если они изменились.

        Возвращает последнюю дату с рыночными данным.
        """
        try:
            timestamp = await self._download()
        except (aiomoex.client.ISSMoexError, ValidationError) as err:
            raise exceptions.DownloadError("trading dates") from err

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

        return _Payload.parse_obj({"df": json}).last_date()

    async def _save(self, timestamp: datetime) -> None:
        table = DatesTable(timestamp=timestamp)

        return await self._repo.save(table)
