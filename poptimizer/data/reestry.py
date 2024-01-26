import asyncio
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Final

import aiohttp
from lxml import html

from poptimizer.core import domain, errors
from poptimizer.data import quotes, raw, status

_URL: Final = "https://закрытияреестров.рф/_/"

_RE_DATE: Final = re.compile(r"\d{1,2}[.]\d{2}[.]\d{4}")
_RE_DIV: Final = re.compile(r"(\d.*)[\xA0\s](руб|USD|\$)")
_DIV_TRANSLATE: Final = str.maketrans({",": ".", " ": ""})


class DivReestry(raw.DivRaw):
    ...


class ReestryDividendsUpdated(domain.Event):
    day: domain.Day


class ReestryDividendsEventHandler:
    def __init__(self, http_client: aiohttp.ClientSession) -> None:
        self._http_client = http_client

    async def handle(self, ctx: domain.Ctx, event: status.DivStatusUpdated) -> None:
        async with asyncio.TaskGroup() as tg:
            for row in event.divs:
                tg.create_task(self._update_one(ctx, event.day, row))

        ctx.publish(ReestryDividendsUpdated(day=event.day))

    async def _update_one(
        self,
        ctx: domain.Ctx,
        update_day: domain.Day,
        row: status.Row,
    ) -> None:
        table = await ctx.get(DivReestry, domain.UID(row.ticker))

        if table.has_day(row.day):
            return

        quotes_table = await ctx.get(quotes.Quotes, for_update=False)
        first_day = quotes_table.df[0].day

        url = await self._find_url(row.ticker_base)
        html_page = await self._load_html(url, row)
        try:
            raw_rows = _parse(html_page, 1 + row.preferred, first_day)
        except errors.DomainError as err:
            raise errors.DomainError(f"can't parse {row.ticker}") from err

        table.update(update_day, raw_rows)

    async def _find_url(self, ticker_base: str) -> str:
        async with self._http_client.get(_URL) as resp:
            if not resp.ok:
                raise errors.DomainError(f"bad respond status {resp.reason}")

            html_page = await resp.text()

        links: list[html.HtmlElement] = html.document_fromstring(html_page).xpath("//*/a")  # type: ignore[reportUnknownMemberType]

        for link in links:
            link_text = link.text_content()
            if ticker_base in link_text or ticker_base.lower() in link_text:
                return _URL + link.attrib["href"]

        raise errors.DomainError(f"{ticker_base} dividends not found")

    async def _load_html(self, url: str, row: status.Row) -> str:
        async with self._http_client.get(url) as resp:
            if not resp.ok:
                raise errors.DomainError(f"{row.ticker} bad respond status {resp.reason}")

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
        raise errors.DomainError(f"wrong dividends table header {header}")


def _parse_rows(rows_iter: Iterable[html.HtmlElement], data_col: int, first_day: domain.Day) -> Iterable[raw.Row]:
    for row in rows_iter:
        if "ИТОГО" in (date_raw := "".join(row[0].itertext())):
            continue

        if "НЕ ВЫПЛАЧИВАТЬ" in (div_raw := "".join(row[data_col].itertext())):
            continue

        div, currency = _parse_div(div_raw)

        if (day := _parse_date(date_raw)) >= first_day:
            yield raw.Row(
                day=day,
                dividend=div,
                currency=currency,
            )


def _parse_date(date_raw: str) -> datetime:
    if not (date_re := _RE_DATE.search(date_raw)):
        raise errors.DomainError(f"can't parse date {date_raw}")

    return datetime.strptime(date_re.group(0), "%d.%m.%Y")


def _parse_div(div_raw: str) -> tuple[float, domain.Currency]:
    if not (div_re := _RE_DIV.search(div_raw)):
        raise errors.DomainError(f"can't parse dividends {div_raw}")

    match div_re[2]:
        case "руб":
            currency = domain.Currency.RUR
        case "USD" | "$":
            currency = domain.Currency.USD
        case _:
            raise errors.DomainError(f"unknown currency {div_re[2]}")

    div = float(div_re[1].translate(_DIV_TRANSLATE))

    return div, currency
