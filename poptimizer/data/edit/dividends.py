"""Редактирование вручную введенных дивидендов."""
from __future__ import annotations

import bisect
import logging
from datetime import datetime
from enum import Enum, unique

from pydantic import BaseModel

from poptimizer.data import domain, exceptions
from poptimizer.data.repo import Repo
from poptimizer.data.update import securities
from poptimizer.data.update.raw import check_raw, nasdaq, reestry


class TickersDTO(BaseModel):
    """Сортированный перечень существующих тикеров."""

    __root__: list[str]


@unique
class Status(Enum):
    """Возможные значения статуса."""

    EXTRA = "extra"
    OK = "ok"
    MISSED = "missed"


class Dividend(BaseModel):
    """Отдельная запись о дивидендах со статусом сравнения."""

    date: datetime
    dividend: float
    currency: domain.Currency
    status: Status


class DividendsDTO(BaseModel):
    """Данные о дивидендах со статусом сравнения с внешними источниками."""

    __root__: list[Dividend]

    @classmethod
    def make_from_comparison(cls, raw: check_raw.Table, source: check_raw.Table) -> DividendsDTO:
        """Добавляет к локальным данным статус сравнения с данными из внешнего источника."""
        dto = []

        for row_raw in raw.df:
            status = Status.OK
            if not source.has_row(row_raw):
                status = Status.EXTRA

            dto.append(
                Dividend(
                    date=row_raw.date,
                    dividend=row_raw.dividend,
                    currency=row_raw.currency,
                    status=status,
                ),
            )

        for row_source in source.df:
            if row_source.is_valid_date() and not raw.has_row(row_source):
                dto.append(
                    Dividend(
                        date=row_source.date,
                        dividend=row_source.dividend,
                        currency=row_source.currency,
                        status=Status.MISSED,
                    ),
                )

        dto.sort(key=lambda dto_row: dto_row.date)

        return cls(__root__=dto)


class SaveDividendsDTO(BaseModel):
    """Обновленные дивиденды для сохранения."""

    __root__: list[check_raw.Raw]


class Service:
    """Сервис редактирования перечня выбранных тикеров."""

    def __init__(self, repo: Repo) -> None:
        self._logger = logging.getLogger("DivEdit")
        self._repo = repo

    async def get_tickers(self) -> TickersDTO:
        """Загружает информацию о тикерах."""
        table = await self._repo.get(securities.Table)

        return TickersDTO(__root__=[row.ticker for row in table.df])

    async def get_dividends(self, ticker: str) -> DividendsDTO:
        """Загружает данные о вручную введенных дивидендах и их соответствии внешним источникам."""
        desc, _ = await self._get_ticker_description(ticker)

        raw = await self._repo.get(check_raw.Table, ticker)

        source_type: type[check_raw.Table] = reestry.Table
        if desc.is_foreign:
            source_type = nasdaq.Table

        source = await self._repo.get(source_type, ticker)

        return DividendsDTO.make_from_comparison(raw, source)

    async def save_dividends(self, ticker: str, dividends: SaveDividendsDTO) -> None:
        """Сохраняет измененные дивиденды."""
        _, timestamp = await self._get_ticker_description(ticker)

        raw = await self._repo.get(check_raw.Table, ticker)

        raw.update(timestamp, dividends.__root__)

        await self._repo.save(raw)

    async def _get_ticker_description(self, ticker: str) -> tuple[securities.Security, datetime]:
        table = await self._repo.get(securities.Table)
        pos = bisect.bisect_left(table.df, ticker, key=lambda row: row.ticker)

        sec = table.df[pos]

        if pos == len(table.df) or sec.ticker != ticker:
            raise exceptions.EditError(f"wrong ticker {ticker}")

        return sec, table.timestamp
