"""Сервис обновления данных о дивидендах в рублях на основе сырых дивидендов."""
import asyncio
import bisect
import logging
from collections.abc import Iterator
from datetime import datetime
from typing import ClassVar

from pydantic import Field, validator

from poptimizer.core import domain, repository
from poptimizer.data import exceptions, validate
from poptimizer.data.update import securities, usd
from poptimizer.data.update.raw import check_raw


class Dividend(domain.Row):
    """Выплата дивидендов в рублях."""

    date: datetime
    dividend: float = Field(gt=0)


class Table(domain.BaseEntity):
    """Таблица дивидендов в рублях."""

    group: ClassVar[domain.Group] = domain.Group.DIVIDENDS
    df: list[Dividend] = Field(default_factory=list[Dividend])

    def update(self, update_day: datetime, rows: list[Dividend]) -> None:
        """Обновляет таблицу."""
        self.timestamp = update_day
        self.df = rows

    _must_be_sorted_by_date = validator("df", allow_reuse=True)(validate.sorted_by_date)
    _must_be_after_start_date = validator("df", allow_reuse=True)(validate.after_start_date)


class Service:
    """Сервис обновления данных о дивидендах в рублях на основе сырых дивидендов.

    Для пересчета долларовых дивидендов используется курс на момент закрытия реестра.
    """

    def __init__(self, repo: repository.Repo) -> None:
        self._logger = logging.getLogger("Dividends")
        self._repo = repo

    async def update(self, update_day: datetime, sec_list: list[securities.Security], usd_list: list[usd.USD]) -> None:
        """Обновляет дивиденды в рублях."""
        coro = [self._update_one(update_day, sec, usd_list) for sec in sec_list]
        await asyncio.gather(*coro)

        self._logger.info("update is completed")

    async def _update_one(self, update_day: datetime, sec: securities.Security, usd_list: list[usd.USD]) -> None:
        table = await self._repo.get(Table, sec.ticker)

        raw_list = (await self._repo.get(check_raw.Table, sec.ticker)).df

        rows = list(_prepare_rows(raw_list, usd_list))

        table.update(update_day, rows)

        await self._repo.save(table)


def _prepare_rows(
    raw_list: list[check_raw.Raw],
    usd_list: list[usd.USD],
) -> Iterator[Dividend]:
    if not raw_list:
        return []

    date = raw_list[0].date
    div = _div_in_rur(raw_list[0], usd_list)

    for row in raw_list[1:]:
        if row.date > date:
            yield Dividend(date=date, dividend=div)

            date = row.date
            div = 0

        div += _div_in_rur(row, usd_list)

    yield Dividend(date=date, dividend=div)


def _div_in_rur(raw_row: check_raw.Raw, usd_list: list[usd.USD]) -> float:
    match raw_row.currency:
        case domain.Currency.RUR:
            return raw_row.dividend
        case domain.Currency.USD:
            pos = bisect.bisect_right(usd_list, raw_row.date, key=lambda usd_row: usd_row.date)

            return raw_row.dividend * usd_list[pos - 1].close
        case _:
            raise exceptions.UpdateError(f"unknown currency {raw_row.currency}")
