"""Обновление таблицы с ожидаемыми дивидендами."""
import csv
import io
import itertools
import logging
import re
from datetime import datetime, timedelta
from typing import ClassVar, Final, Iterator

import aiohttp
from pydantic import Field, validator

from poptimizer.core import domain, repository, viewer
from poptimizer.data import exceptions
from poptimizer.data.update import securities

_URL: Final = "https://www.moex.com/ru/listing/listing-register-closing-csv.aspx"
_LOOK_BACK_DAYS: Final = 14
_DATE_FMT: Final = "%d.%m.%Y %H:%M:%S"
_RE_TICKER = re.compile(r", ([A-Z]+-[A-Z]+|[A-Z]+) \[")


class Status(domain.Row):
    """Информация о новых дивидендах."""

    ticker: str
    ticker_base: str
    preferred: bool
    foreign: bool
    date: datetime


class Table(domain.BaseEntity):
    """Таблица с информацией о новых дивидендах."""

    group: ClassVar[domain.Group] = domain.Group.STATUS
    df: list[Status] = Field(default_factory=list[Status])

    def update(self, update_day: datetime, rows: list[Status]) -> None:
        """Обновляет таблицу."""
        self.timestamp = update_day

        rows.sort(key=(lambda status: (status.ticker, status.date)))

        self.df = rows

    @validator("df")
    def _must_be_sorted_by_ticker_and_date(cls, df: list[Status]) -> list[Status]:
        ticker_date_pairs = itertools.pairwise((row.ticker, row.date) for row in df)

        if not all(ticker_date <= next_ for ticker_date, next_ in ticker_date_pairs):
            raise ValueError("ticker and dates are not sorted")

        return df


class Service:
    """Сервис загрузки статуса дивидендов."""

    def __init__(self, repo: repository.Repo, session: aiohttp.ClientSession, port_viewer: viewer.Portfolio) -> None:
        self._logger = logging.getLogger("Status")
        self._repo = repo
        self._session = session
        self._viewer = port_viewer

    async def update(self, update_day: datetime, sec: list[securities.Security]) -> list[Status]:
        """Обновляет статус дивидендов и логирует неудачную попытку."""
        try:
            status = await self._update(update_day, sec)
        except exceptions.DataUpdateError as err:
            self._logger.warning(f"can't complete update -> {err}")

            return []

        self._logger.info("update is completed")

        return status

    async def _update(self, update_day: datetime, sec: list[securities.Security]) -> list[Status]:
        table = await self._repo.get(Table)

        csv_file = await self._download()
        selected = set(await self._viewer.tickers())
        row = self._parse(csv_file, selected, sec)

        table.update(update_day, row)

        await self._repo.save(table)

        return table.df

    async def _download(self) -> io.StringIO:
        async with self._session.get(_URL) as resp:
            if not resp.ok:
                raise exceptions.DataUpdateError(f"bad dividends status respond {resp.reason}")

            return io.StringIO(await resp.text(), newline="")

    def _parse(
        self,
        csv_file: io.StringIO,
        selected: set[str],
        sec: list[securities.Security],
    ) -> list[Status]:
        """Первая строка содержит заголовок, поэтому пропускается."""
        reader = csv.reader(csv_file)
        next(reader)

        return list(
            _status_gen(
                self._parsed_rows_gen(reader),
                selected,
                {row.ticker: row for row in sec},
            ),
        )

    def _parsed_rows_gen(
        self,
        reader: Iterator[list[str]],
    ) -> Iterator[tuple[str, datetime]]:
        for ticker_raw, date_raw, *_ in reader:
            date = datetime.strptime(date_raw, _DATE_FMT)

            if date < datetime.now() - timedelta(days=_LOOK_BACK_DAYS):
                continue

            if (ticker_re := _RE_TICKER.search(ticker_raw)) is None:
                self._logger.warning(f"can't parse ticker {ticker_raw}")

                continue

            yield ticker_re[1], date


def _status_gen(
    raw_rows: Iterator[tuple[str, datetime]],
    selected: set[str],
    sec_hash: dict[str, securities.Security],
) -> Iterator[Status]:
    for ticker, date in raw_rows:
        if ticker in selected:
            sec_desc = sec_hash[ticker]
            yield Status(
                ticker=ticker,
                ticker_base=sec_desc.ticker_base,
                preferred=sec_desc.is_preferred,
                foreign=sec_desc.is_foreign,
                date=date,
            )
