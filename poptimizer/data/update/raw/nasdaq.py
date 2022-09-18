"""Сервис обновления дивидендов с сайта https://www.nasdaq.com."""
import asyncio
import logging
from datetime import datetime
from typing import Any, ClassVar, Final

import aiohttp
from pydantic import BaseModel, Field, validator

from poptimizer.core import domain, repository
from poptimizer.data import exceptions
from poptimizer.data.update.raw import check_raw, status

_URL: Final = "https://api.nasdaq.com/api/quote/{ticker}/dividends?assetclass=stocks"
_NO_DATE: Final = "N/A"
_CURRENCY_PREFIX: Final = "$"


class _Row(BaseModel):
    date: datetime | None = Field(alias="recordDate")
    dividend: tuple[float, domain.Currency] = Field(alias="amount")

    @validator("date", pre=True)
    def _parse_nasdaq_date(cls, date: str) -> datetime | None:
        if date == _NO_DATE:
            return None

        return datetime.strptime(date, "%m/%d/%Y")

    @validator("dividend", pre=True)
    def _parse_nasdaq_dividend(cls, dividend: str) -> tuple[float, domain.Currency]:
        if not dividend.startswith(_CURRENCY_PREFIX):
            raise ValueError(f"unknown currency {dividend[0]}")

        dividend = dividend.removeprefix(_CURRENCY_PREFIX)

        return float(dividend), domain.Currency.USD


class _DividendsRows(BaseModel):
    rows: list[_Row]


class _Dividends(BaseModel):
    dividends: _DividendsRows


class _NASDAQ(BaseModel):
    """Представляет структуру json-ответа https://www.nasdaq.com."""

    api_data: _Dividends = Field(alias="data")


class Table(check_raw.Table):
    """Таблица дивидендов сайта https://www.nasdaq.com."""

    group: ClassVar[domain.Group] = domain.Group.NASDAQ


class Service:
    """Сервис обновления дивидендов с сайта https://www.nasdaq.com."""

    def __init__(self, repo: repository.Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger("NASDAQ")
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime, status_rows: list[status.Status]) -> None:
        """Обновляет дивидендов с сайта https://www.nasdaq.com."""
        coro = [self._update_one(update_day, row) for row in status_rows if row.foreign]
        await asyncio.gather(*coro)

        self._logger.info("update is completed")

    async def _update_one(self, update_day: datetime, status_row: status.Status) -> None:
        table = await self._repo.get(Table, status_row.ticker)

        if table.has_date(status_row.date):
            return

        json = await self._download(status_row)
        row = _parse(json)

        table.update(update_day, row)

        await self._repo.save(table)

    async def _download(self, status_row: status.Status) -> Any:
        url = _URL.format(ticker=status_row.ticker_base)

        async with self._session.get(url) as resp:
            if not resp.ok:
                raise exceptions.UpdateError(f"{status_row.ticker} bad respond status {resp.reason}")

            return await resp.json()


def _parse(json: Any) -> list[check_raw.Raw]:
    return [
        check_raw.Raw(
            date=row.date,
            dividend=row.dividend[0],
            currency=row.dividend[1],
        )
        for row in _NASDAQ.parse_obj(json).api_data.dividends.rows
        if row.date
    ]
