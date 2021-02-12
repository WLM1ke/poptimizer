"""Обновление данных с https://finrange.com/."""
import re
from typing import Optional

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import chromium, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга
URL_START = "https://finrange.com/company/"
URL_END = "/dividends"
DIV_PATTERN = r".*\d\s\s[$₽]"
TABLE_NUM = 2


def _div_parser(div: str) -> Optional[str]:
    re_div = re.search(DIV_PATTERN, div)
    if re_div:
        div_string = re_div.group(0)
        div_string = div_string.replace(",", ".")
        return div_string.replace(" ", "")
    return None


def _prepare_url(ticker: str) -> str:
    if ticker[-3:] == "-RM":
        ticker = ticker[:-3]
    return "".join([URL_START, ticker, URL_END])


async def _load_ticker_page(url: str, browser: chromium.Browser = chromium.BROWSER) -> str:
    page = await browser.get_new_page()

    await page.goto(url)
    await page.waitForXPath("//*[@id='filter-3']/div[2]/div[2]/div/table")
    return await page.content()


def _get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=1,
        raw_name=("Дата закрытия реестра акционеров",),
        name=col.DATE,
        parser_func=description.date_parser,
    )
    div_col = description.ColDesc(
        num=3,
        raw_name=("Дивиденд на акцию",),
        name=ticker,
        parser_func=_div_parser,
    )
    return [date_col, div_col]


class FinRangeGateway(gateways.DivGateway):
    """Обновление данных с https://finrange.com/.."""

    _logger = adapters.AsyncLogger()

    async def get(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        url = _prepare_url(ticker)
        html = await _load_ticker_page(url)

        cols_desc = _get_col_desc(ticker)

        try:
            df = parser.get_df_from_html(html, TABLE_NUM, cols_desc)
        except description.ParserError:
            return pd.DataFrame(columns=[ticker, col.CURRENCY])

        ticker_col = df[ticker]
        df[col.CURRENCY] = ticker_col.str.slice(start=-1)
        df[col.CURRENCY] = df[col.CURRENCY].map(
            {
                "₽": col.RUR,
                "$": col.USD,
            },
        )

        ticker_col = ticker_col.str.slice(stop=-1)
        df[ticker] = ticker_col.apply(float)

        return df.sort_index(axis=0)
