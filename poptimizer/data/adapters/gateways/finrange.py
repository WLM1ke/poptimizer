"""Обновление данных с https://finrange.com/."""
from typing import Optional, cast

import pandas as pd
from pyppeteer import errors

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, chromium, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга
URL_START = "https://finrange.com/company/"
URL_END = "/dividends"
TABLE_XPATH = "//*[@id='app']/div[1]/section/div/div[3]/div[3]/div[2]/div[2]/div/table"
TABLE_NUM = 1


def _prepare_url(ticker: str) -> str:
    if ticker[-3:] == "-RM":
        ticker = ticker[:-3]
    return "".join([URL_START, ticker, URL_END])


async def _get_page_html(url: str, browser: chromium.Browser = chromium.BROWSER) -> str:
    async with browser.get_new_page() as page:
        await page.goto(url)

        try:
            await page.waitForXPath(TABLE_XPATH)
        except errors.TimeoutError:
            return cast(str, await page.content())

        return cast(str, await page.content())


def _get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=2,
        raw_name=("Дата закрытия реестра акционеров",),
        name=col.DATE,
        parser_func=cell_parser.date_ru,
    )
    div_col = description.ColDesc(
        num=4,
        raw_name=("Дивиденд на акцию",),
        name=ticker,
        parser_func=cast(parser.ParseFuncType, cell_parser.div_with_cur),
    )
    return [date_col, div_col]


class FinRangeGateway(gateways.DivGateway):
    """Обновление данных с https://finrange.com/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> Optional[pd.DataFrame]:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        url = _prepare_url(ticker)
        html = await _get_page_html(url)
        cols_desc = _get_col_desc(ticker)

        try:
            df = parser.get_df_from_html(html, TABLE_NUM, cols_desc)
        except description.ParserError:
            return None

        return description.reformat_df_with_cur(df, ticker)
