"""Сервис обновления дивидендов с сайта https://закрытияреестров.рф."""
import asyncio
import logging
import re
from collections.abc import Iterable
from datetime import datetime
from typing import ClassVar, Final

import aiohttp
from lxml import html  # noqa: S410

from poptimizer.data import domain, exceptions
from poptimizer.data.repo import Repo
from poptimizer.data.update.raw import check_raw, status

_URL: Final = "https://закрытияреестров.рф/"

_RE_DATE: Final = re.compile(r"\d{1,2}\.\d{2}\.\d{4}")
_RE_DIV: Final = re.compile(r"(\d.*)[\xA0\s](руб|USD|\$)")
_DIV_TRANSLATE: Final = str.maketrans({",": ".", " ": ""})


class Table(check_raw.Table):
    """Таблица дивидендов сайта https://закрытияреестров.рф."""

    group: ClassVar[domain.Group] = domain.Group.REESTRY


class Service:
    """Сервис обновления дивидендов с сайта https://закрытияреестров.рф."""

    def __init__(self, repo: Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger("Reestry")
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime, status_rows: list[status.Status]) -> None:
        """Обновляет дивидендов с сайта https://закрытияреестров.рф."""
        coro = [self._update_one(update_day, row) for row in status_rows if not row.foreign]
        await asyncio.gather(*coro)

        self._logger.info("update is completed")

    async def _update_one(self, update_day: datetime, status_row: status.Status) -> None:
        table = await self._repo.get(Table, status_row.ticker)

        if table.has_date(status_row.date):
            return

        html_page = await self._download(status_row)
        row = _parse(html_page, status_row.preferred)

        table.update(update_day, row)

        await self._repo.save(table)

    async def _download(self, status_row: status.Status) -> str:
        """У Русала особый тикер на сайте, не совпадающий с обычным."""
        ticker = status_row.ticker_base
        if ticker == "RUAL":
            ticker = "RUALR"

        async with self._session.get(f"{_URL}{ticker}") as resp:
            if not resp.ok:
                raise exceptions.UpdateError(f"{status_row.ticker} bad respond status {resp.reason}")

            return await resp.text()


def _parse(html_page: str, preferred: bool) -> list[check_raw.Raw]:
    doc = html.document_fromstring(html_page)
    rows_iter = iter(doc.xpath("//*/table/tbody/tr"))
    data_col = 1 + preferred

    _validate_header(next(rows_iter), data_col)

    return list(_parse_data(rows_iter, data_col))


def _validate_header(row: html.HtmlElement, data_col: int) -> None:
    share_type = "привилегированную"
    if data_col == 1:
        share_type = "обыкновенную"

    if share_type not in (header := html.tostring(row[data_col], encoding="unicode")):
        raise exceptions.UpdateError(f"wrong header {header}")


def _parse_data(rows_iter: Iterable[html.HtmlElement], data_col: int) -> Iterable[check_raw.Raw]:
    for row in rows_iter:
        if "ИТОГО" in (date_raw := "".join(row[0].itertext())):
            continue

        if "НЕ ВЫПЛАЧИВАТЬ" in (div_raw := "".join(row[data_col].itertext())):
            continue

        div, currency = _parse_div(div_raw)

        yield check_raw.Raw(
            date=_parse_date(date_raw),
            dividend=div,
            currency=currency,
        )


def _parse_date(date_raw: str) -> datetime:
    if not (date_re := _RE_DATE.search(date_raw)):
        raise exceptions.UpdateError(f"can't parse date {date_raw}")

    return datetime.strptime(date_re.group(0), "%d.%m.%Y")


def _parse_div(div_raw: str) -> tuple[float, domain.Currency]:
    if not (div_re := _RE_DIV.search(div_raw)):
        raise exceptions.UpdateError(f"can't parse dividends {div_raw}")

    match div_re[2]:
        case "руб":
            currency = domain.Currency.RUR
        case "USD" | "$":
            currency = domain.Currency.USD
        case _:
            raise exceptions.UpdateError(f"unknown currency {div_re[2]}")

    div = float(div_re[1].translate(_DIV_TRANSLATE))

    return div, currency
