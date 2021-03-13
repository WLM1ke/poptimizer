"""Обновление данных с https://www.nasdaq.com/."""
from typing import Final, Optional, cast

import pandas as pd
from pyppeteer import errors

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, chromium, description, parser
from poptimizer.shared import adapters, col

# Адрес и xpath таблицы
URL_START = "https://www.nasdaq.com/market-activity/stocks/"
URL_END = "/dividend-history"
TABLE_XPATH: Final = "/html/body/div[2]/div/main/div[2]/div[4]/div[2]/div/div[2]/div[2]/div[2]/table"

# Задержка для частичной загрузки в микросекундах
PARTIAL_LOAD_TIMEOUT: Final = 1000


def get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=4,
        raw_name=("RECORD DATE",),
        name=col.DATE,
        parser_func=cell_parser.date_us,
    )
    div_col = description.ColDesc(
        num=2,
        raw_name=("CASH AMOUNT",),
        name=ticker,
        parser_func=cell_parser.div_us,
    )
    return [date_col, div_col]


async def _load_ticker_page(url: str, browser: chromium.Browser = chromium.BROWSER) -> str:
    """Загружает страницу с таблицей дивидендов."""
    async with browser.get_new_page() as page:
        try:
            # На странице много рекламных банеров - она практически никогда не загружается полностью
            # Достаточно немного подождать для частичного перехода, а потом ждать только загрузки таблицы
            await page.goto(url, options={"timeout": PARTIAL_LOAD_TIMEOUT})
        except errors.TimeoutError:
            await page.waitForXPath(TABLE_XPATH)

        return cast(str, await page.content())


class NASDAQGateway(gateways.DivGateway):
    """Обновление данных с https://www.nasdaq.com/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> Optional[pd.DataFrame]:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        cols_desc = get_col_desc(ticker)

        url = "".join([URL_START, ticker[:-3], URL_END])
        html = await _load_ticker_page(url)
        try:
            df = parser.get_df_from_html(html, 0, cols_desc)
        except description.ParserError:
            return None

        df = df.groupby(lambda date: date).sum()
        df[col.CURRENCY] = col.USD
        return df
