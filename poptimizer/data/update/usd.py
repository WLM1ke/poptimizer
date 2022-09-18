"""Служба, обновляющая котировки курса доллара."""
import logging
from datetime import datetime
from typing import ClassVar

import aiohttp
import aiomoex
from pydantic import Field, validator

from poptimizer.core import domain, repository
from poptimizer.data import exceptions, validate


class USD(domain.Row):
    """Котировки курса доллара."""

    date: datetime = Field(alias="begin")
    open: float = Field(alias="open", gt=0)
    close: float = Field(alias="close", gt=0)
    high: float = Field(alias="high", gt=0)
    low: float = Field(alias="low", gt=0)
    turnover: float = Field(alias="value", gt=0)


class Table(domain.BaseEntity):
    """Таблица с котировками курса доллара."""

    group: ClassVar[domain.Group] = domain.Group.USD
    df: list[USD] = Field(default_factory=list[USD])

    def update(self, update_day: datetime, rows: list[USD]) -> None:
        """Обновляет таблицу."""
        self.timestamp = update_day

        if not self.df:
            self.df = rows

            return

        last = self.df[-1]

        if last != (first := rows[0]):
            raise exceptions.UpdateError(f"{self.id_} data missmatch {last} vs {first}")

        self.df.extend(rows[1:])

    def last_row_date(self) -> datetime | None:
        """Дата последней строки при наличии."""
        if not self.df:
            return None

        return self.df[-1].date

    _must_be_sorted_by_date = validator("df", allow_reuse=True)(validate.sorted_by_date)


class Service:
    """Сервис обновления котировок курса доллара."""

    def __init__(self, repo: repository.Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger("USD")
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime) -> list[USD]:
        """Обновляет котировки курса доллара."""
        rows = await self._update(update_day)

        self._logger.info("update is completed")

        return rows

    async def _update(self, update_day: datetime) -> list[USD]:
        table = await self._repo.get(Table)

        start_date = table.last_row_date()
        rows = await self._download(start_date, update_day)

        table.update(update_day, rows)

        await self._repo.save(table)

        return table.df

    async def _download(
        self,
        start_date: datetime | None,
        update_day: datetime,
    ) -> list[USD]:
        json = await aiomoex.get_market_candles(
            session=self._session,
            start=start_date and str(start_date.date()),
            end=str(update_day.date()),
            interval=24,
            security="USD000UTSTOM",
            market="selt",
            engine="currency",
        )

        return domain.Rows[USD].parse_obj(json).__root__
