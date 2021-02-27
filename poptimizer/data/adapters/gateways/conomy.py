"""Загрузка данных с https://www.conomy.ru/."""
import asyncio
from typing import Final, Optional, cast

import pandas as pd
from pyppeteer import errors
from pyppeteer.page import Page

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, chromium, description, parser
from poptimizer.shared import adapters, col

# Параметры поиска страницы эмитента
SEARCH_URL: Final = "https://www.conomy.ru/search"
SEARCH_FIELD: Final = '//*[@id="issuer_search"]'

# Параметры поиска данных по дивидендам
DIVIDENDS_MENU: Final = '//*[@id="page-wrapper"]/div/nav/ul/li[5]/a'
DIVIDENDS_TABLE: Final = '//*[@id="page-container"]/div[2]/div/div[1]'

# Номер таблицы на html-странице и строки с заголовком
TABLE_INDEX: Final = 1

# Задержка для принудительной остановки Chromium
CHROMIUM_TIMEOUT = 30


async def _load_ticker_page(page: Page, ticker: str) -> None:
    """Вводит в поле поиска тикер и переходит на страницу с информацией по эмитенту."""
    await page.goto(SEARCH_URL)
    await page.waitForXPath(SEARCH_FIELD)
    element, *_ = await page.xpath(SEARCH_FIELD)
    await element.type(ticker)
    await element.press("Enter")


async def _load_dividends_table(page: Page) -> None:
    """Выбирает на странице эмитента меню дивиденды и дожидается загрузки таблиц с ними."""
    await page.waitForXPath(DIVIDENDS_MENU)
    element, *_ = await page.xpath(DIVIDENDS_MENU)
    await element.click()
    await page.waitForXPath(DIVIDENDS_TABLE)


async def _get_html(ticker: str, browser: chromium.Browser = chromium.BROWSER) -> str:
    """Возвращает html-код страницы с данными по дивидендам с сайта https://www.conomy.ru/."""
    async with browser.get_new_page() as page:
        await _load_ticker_page(page, ticker)
        await _load_dividends_table(page)
        return cast(str, await page.content())


def _get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием необходимых столбцов."""
    date = description.ColDesc(
        num=5,
        raw_name=("E", "Дата закрытия реестра акционеров", "Под выплату дивидендов"),
        name=col.DATE,
        parser_func=cell_parser.date_ru,
    )
    columns = [date]

    if description.is_common(ticker):
        common = description.ColDesc(
            num=7,
            raw_name=("G", "Размер дивидендов", "АОИ"),
            name=ticker,
            parser_func=cell_parser.div_ru,
        )
        columns.append(common)
        return columns

    preferred = description.ColDesc(
        num=8,
        raw_name=("H", "Размер дивидендов", "АПИ"),
        name=ticker,
        parser_func=cell_parser.div_ru,
    )
    columns.append(preferred)
    return columns


class ConomyGateway(gateways.DivGateway):
    """Обновление для таблиц с дивидендами на https://www.conomy.ru/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> Optional[pd.DataFrame]:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        try:
            # На некоторых компьютерах/операционных системах Chromium перестает реагировать на команды
            # Поэтому загрузка принудительно приостанавливается
            html = await asyncio.wait_for(_get_html(ticker), timeout=CHROMIUM_TIMEOUT)
        except (errors.TimeoutError, asyncio.exceptions.TimeoutError):
            return None

        cols_desc = _get_col_desc(ticker)
        df = parser.get_df_from_html(html, TABLE_INDEX, cols_desc)
        df = df.dropna()

        df = self._sort_and_agg(df)
        df[col.CURRENCY] = col.RUR
        return df
