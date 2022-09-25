"""Служба загрузки котировок ценных бумаг."""
import asyncio
import logging
from datetime import datetime
from typing import ClassVar

import aiohttp
import aiomoex
from pydantic import Field, validator

from poptimizer.app import retry
from poptimizer.core import consts, domain, repository
from poptimizer.data import exceptions, validate
from poptimizer.data.update import securities


class Quote(domain.Row):
    """Котировка ценной бумаги."""

    date: datetime = Field(alias="begin")
    open: float = Field(alias="open", gt=0)
    close: float = Field(alias="close", gt=0)
    high: float = Field(alias="high", gt=0)
    low: float = Field(alias="low", gt=0)
    turnover: float = Field(alias="value", ge=0)


class Table(domain.BaseEntity):
    """Таблица с котировками ценных бумаг."""

    group: ClassVar[domain.Group] = domain.Group.QUOTES
    df: list[Quote] = Field(default_factory=list[Quote])

    def update(self, update_day: datetime, rows: list[Quote]) -> None:
        """Обновляет таблицу."""
        self.timestamp = update_day

        if not self.df:
            rows.sort(key=lambda row: row.date)
            self.df = rows

            return

        last = self.df[-1]

        if last != (first := rows[0]):
            raise exceptions.DataUpdateError(f"{self.id_} data missmatch {last} vs {first}")

        self.df.extend(rows[1:])

    def last_row_date(self) -> datetime | None:
        """Дата последней строки при наличии."""
        if not self.df:
            return None

        return self.df[-1].date

    _must_be_sorted_by_date = validator("df", allow_reuse=True)(validate.sorted_by_date)
    _must_be_after_start_date = validator("df", allow_reuse=True)(validate.after_start_date)


class Service:
    """Сервис обновления котировок ценных бумаг."""

    def __init__(self, repo: repository.Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger("Quotes")
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime, sec_list: list[securities.Security]) -> None:
        """Обновляет котировки ценных бумаг."""
        coro = [self._update_one(update_day, sec) for sec in sec_list]
        await asyncio.gather(*coro)

        self._logger.info("update is completed")

    async def _update_one(self, update_day: datetime, sec: securities.Security) -> None:
        table = await self._repo.get(Table, sec.ticker)

        start_date = table.last_row_date() or consts.START_DATE
        rows = await self._download(sec, start_date, update_day)

        table.update(update_day, rows)

        await self._repo.save(table)

    @retry.AsyncExponential(
        retry.Policy(
            attempts=3,
            start_timeout_sec=60,
            factor=2,
            exceptions=exceptions.DataUpdateError,
        ),
        logger=logging.getLogger("Quotes"),
    )
    async def _download(
        self,
        sec: securities.Security,
        start_date: datetime | None,
        update_day: datetime,
    ) -> list[Quote]:
        match sec.board:
            case "TQBR" | "TQTF":
                market = "shares"
            case "FQBR":
                market = "foreignshares"
            case _:
                raise exceptions.DataUpdateError(f"unknown board {sec.board} for ticker {sec.ticker}")

        try:
            json = await aiomoex.get_market_candles(
                session=self._session,
                start=start_date and str(start_date.date()),
                end=str(update_day.date()),
                interval=24,
                security=sec.ticker,
                market=market,
                engine="stock",
            )
        except (aiohttp.client_exceptions.ClientConnectorError, asyncio.TimeoutError) as err:
            raise exceptions.DataUpdateError(f"can't download {sec.board}.{sec.ticker}") from err

        return domain.Rows[Quote].parse_obj(json).__root__
