"""Обновление данных с https://finrange.com/."""

import pandas as pd
from pyppeteer import errors

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import chromium, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга
URL_START = "https://finrange.com/company/"
URL_END = "/dividends"
TABLE_XPATH = "//*[@id='filter-3']/div[2]/div[2]/div/table"
TABLE_NUM = 2


def _prepare_url(ticker: str) -> str:
    if ticker[-3:] == "-RM":
        ticker = ticker[:-3]
    return "".join([URL_START, ticker, URL_END])


async def _get_page_html(url: str, browser: chromium.Browser = chromium.BROWSER) -> str:
    page = await browser.get_new_page()

    await page.goto(url)

    try:
        await page.waitForXPath(TABLE_XPATH)
    except errors.TimeoutError:
        return await page.content()

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
        parser_func=description.div_parser_with_cur,
    )
    return [date_col, div_col]


class FinRangeGateway(gateways.DivGateway):
    """Обновление данных с https://finrange.com/.."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        url = _prepare_url(ticker)
        html = await _get_page_html(url)
        cols_desc = _get_col_desc(ticker)

        try:
            df = parser.get_df_from_html(html, TABLE_NUM, cols_desc)
        except description.ParserError:
            return pd.DataFrame(columns=[ticker, col.CURRENCY])

        return description.reformat_df_with_cur(df, ticker)
