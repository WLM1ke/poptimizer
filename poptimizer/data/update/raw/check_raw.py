"""Сервис проверки наличия сырых данных по ожидаемым дивидендам."""
import asyncio
import bisect
import itertools
import logging
from datetime import datetime
from typing import ClassVar

from pydantic import Field, validator

from poptimizer import consts
from poptimizer.data import domain, exceptions, repo
from poptimizer.data.update.raw import status


class Raw(domain.Row):
    """Информация о дивидендах с указанием валюты."""

    date: datetime
    dividend: float = Field(gt=0)
    currency: domain.Currency

    def to_tuple(self) -> tuple[datetime, float, domain.Currency]:
        """Преобразует в кортеж для удобства сравнения."""
        return self.date, self.dividend, self.currency

    def is_valid_date(self) -> bool:
        """Дата после начала сбора статистики."""
        return self.date >= consts.START_DATE


class Table(domain.Table):
    """Таблица дивидендов с указанием валюты введенная в ручную."""

    group: ClassVar[domain.Group] = domain.Group.RAW_DIV
    df: list[Raw] = Field(default_factory=list[Raw])

    def update(self, update_day: datetime, rows: list[Raw]) -> None:
        """Обновляет таблицу."""
        self.timestamp = update_day

        rows.sort(key=lambda row: row.to_tuple())

        self.df = rows

    def has_date(self, date: datetime) -> bool:
        """Проверяет, есть ли в таблице указанная дата."""
        df = self.df
        pos = bisect.bisect_left(df, date, key=lambda row: row.date)

        return pos != len(df) and df[pos].date == date

    def has_row(self, raw_row: Raw) -> bool:
        """Проверяет, есть ли соответсвующая строка в таблице."""
        df = self.df
        pos = bisect.bisect_left(
            df,
            raw_row.to_tuple(),
            key=lambda row: row.to_tuple(),
        )

        return pos != len(df) and raw_row == df[pos]

    @validator("df")
    def _sorted_by_date_div_currency(cls, df: list[Raw]) -> list[Raw]:
        """Валидирует сортировку списка по полю даты, дивидендам и валюте по возрастанию."""
        dates_pairs = itertools.pairwise(row.to_tuple() for row in df)

        if not all(row < next_ for row, next_ in dates_pairs):
            raise ValueError("raw dividends are not sorted")

        return df


class Service:
    """Сервис проверки наличия данных по ожидаемым дивидендам."""

    def __init__(self, repository: repo.Repo) -> None:
        self._logger = logging.getLogger("CheckRaw")
        self._repo = repository

    async def check(self, status_rows: list[status.Status]) -> None:
        """Проверяет, что все даты ожидаемых дивидендов имеются во вручную введенных дивидендах."""
        coro = [self._check_one(row) for row in status_rows]

        try:
            await asyncio.gather(*coro)
        except exceptions.DataError as err:
            self._logger.warning(f"can't complete check {err}")

            return

        self._logger.info("check is completed")

    async def _check_one(self, status_row: status.Status) -> None:
        table = await self._repo.get(Table, status_row.ticker)

        if not table.has_date(status_row.date):
            date = status_row.date.date()
            self._logger.warning(f"{status_row.ticker} missed dividend at {date}")
