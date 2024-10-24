import asyncio
import logging
import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Final

import aiohttp
from lxml import html

from poptimizer import errors
from poptimizer.domain import domain
from poptimizer.domain.div import raw, reestry, status
from poptimizer.domain.moex import quotes
from poptimizer.use_cases import handler

_URL: Final = "https://закрытияреестров.рф/_/"

_RE_DATE: Final = re.compile(r"\d{1,2}[.]\d{2}[.]\d{4}")
_RE_DIV: Final = re.compile(r"(\d.*)[\xA0\s](руб|USD|\$)")
_DIV_TRANSLATE: Final = str.maketrans({",": ".", " ": ""})


class ReestryHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._lgr = logging.getLogger()
        self._http_client = http_client

    async def __call__(self, ctx: handler.Ctx, msg: handler.DivStatusUpdated) -> None:
        status_table = await ctx.get(status.DivStatus)

        async with asyncio.TaskGroup() as tg:
            for row in status_table.df:
                tg.create_task(self._update_one(ctx, msg.day, row))

    async def _update_one(
        self,
        ctx: handler.Ctx,
        update_day: domain.Day,
        row: status.Row,
    ) -> None:
        table = await ctx.get_for_update(reestry.DivReestry, domain.UID(row.ticker))

        if table.has_day(row.day):
            return

        quotes_table = await ctx.get(quotes.Quotes, domain.UID(row.ticker))
        first_day = quotes_table.df[0].day

        try:
            url = await self._find_url(row.ticker_base)
        except (TimeoutError, aiohttp.ClientError, errors.UseCasesError) as err:
            self._lgr.warning("Can't find url for %s %s", row.ticker, err)

            return

        try:
            html_page = await self._load_html(url, row.ticker)
        except (TimeoutError, aiohttp.ClientError, errors.UseCasesError) as err:
            self._lgr.warning("Can't load url for %s %s", row.ticker, err)

            return

        try:
            raw_rows = _parse(html_page, 1 + row.preferred, first_day)
        except errors.UseCasesError as err:
            self._lgr.warning("Can't parse %s raw dividends data %s", row.ticker, err)

            return

        table.update(update_day, raw_rows)

    async def _find_url(self, ticker_base: str) -> str:
        async with self._http_client.get(_URL) as resp:
            if not resp.ok:
                raise errors.UseCasesError(f"bad respond status {resp.reason}")

            html_page = await resp.text()

        links: list[html.HtmlElement] = html.document_fromstring(html_page).xpath("//*/a")  # type: ignore[reportUnknownMemberType]

        for link in links:
            link_text = link.text_content()
            if ticker_base in link_text or ticker_base.lower() in link_text:
                return _URL + link.attrib["href"]

        raise errors.UseCasesError(f"{ticker_base} dividends not found")

    async def _load_html(self, url: str, ticker: domain.Ticker) -> str:
        async with self._http_client.get(url) as resp:
            if not resp.ok:
                raise errors.UseCasesError(f"{ticker} bad respond status {resp.reason}")

            return await resp.text()


def _parse(html_page: str, data_col: int, first_day: domain.Day) -> list[raw.Row]:
    rows: list[html.HtmlElement] = html.document_fromstring(html_page).xpath("//*/table/tbody/tr")  # type: ignore[reportUnknownMemberType]

    rows_iter = iter(rows)
    _validate_header(next(rows_iter), data_col)

    return list(_parse_rows(rows_iter, data_col, first_day))


def _validate_header(row: html.HtmlElement, data_col: int) -> None:
    share_type: tuple[str, ...] = ("привилегированную",)
    if data_col == 1:
        share_type = ("обыкновенную", "ГДР")

    header = html.tostring(row[data_col], encoding="unicode")

    if not any(word in header for word in share_type):
        raise errors.UseCasesError(f"wrong dividends table header {header}")


def _parse_rows(rows_iter: Iterable[html.HtmlElement], data_col: int, first_day: domain.Day) -> Iterable[raw.Row]:
    for row in rows_iter:
        if "ИТОГО" in (date_raw := "".join(row[0].itertext())):
            continue

        if "НЕ ВЫПЛАЧИВАТЬ" in (raw_row := "".join(row[data_col].itertext())):
            continue

        div = _parse_div(raw_row)

        if (day := _parse_date(date_raw)) < first_day:
            break

        yield raw.Row(
            day=day,
            dividend=div,
        )


def _parse_date(date_raw: str) -> date:
    if not (date_re := _RE_DATE.search(date_raw)):
        raise errors.UseCasesError(f"can't parse date {date_raw}")

    return datetime.strptime(date_re.group(0), "%d.%m.%Y").date()


def _parse_div(raw_row: str) -> float:
    if not (div_re := _RE_DIV.search(raw_row)):
        raise errors.UseCasesError(f"can't parse dividends {raw_row}")

    match div_re[2]:
        case "руб":
            return float(div_re[1].translate(_DIV_TRANSLATE))
        case _:
            raise errors.UseCasesError(f"unknown currency {div_re[2]}")
