"""Загрузка данных с https://www.conomy.ru/."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, cast

import pandas as pd
import pyppeteer
from pyppeteer.browser import Browser
from pyppeteer.page import Page

from poptimizer.data.core import ports
from poptimizer.data.adapters.updaters import names, parser

logger = logging.getLogger(__name__)

# Параметры поиска страницы эмитента
SEARCH_URL = "https://www.conomy.ru/search"
SEARCH_FIELD = '//*[@id="issuer_search"]'

# Параметры поиска данных по дивидендам
DIVIDENDS_MENU = '//*[@id="page-wrapper"]/div/nav/ul/li[5]/a'
DIVIDENDS_TABLE = '//*[@id="page-container"]/div[2]/div/div[1]'

# Номер таблицы на html-странице и строки с заголовком
TABLE_INDEX = 1

# Параметры проверки обыкновенная акция или привилегированная
COMMON_TICKER_LENGTH = 4
PREFERRED_TICKER_ENDING = "P"


@asynccontextmanager
async def get_browser() -> Browser:
    """Асинхронный браузер с автоматическим закрытием после использования."""
    browser = await pyppeteer.launch()
    try:
        yield browser
    finally:
        await browser.close()


async def load_ticker_page(page: Page, ticker: str) -> None:
    """Вводит в поле поиска тикер и переходит на страницу с информацией по эмитенту."""
    await page.goto(SEARCH_URL)
    await page.waitForXPath(SEARCH_FIELD)
    element, *_ = await page.xpath(SEARCH_FIELD)
    await element.type(ticker)
    await element.press("Enter")


async def load_dividends_table(page: Page) -> None:
    """Выбирает на странице эмитента меню дивиденды и дожидается загрузки таблиц с ними."""
    await page.waitForXPath(DIVIDENDS_MENU)
    element, *_ = await page.xpath(DIVIDENDS_MENU)
    await element.click()
    await page.waitForXPath(DIVIDENDS_TABLE)


async def get_html(ticker: str) -> str:
    """Возвращает html-код страницы с данными по дивидендам с сайта https://www.conomy.ru/."""
    async with get_browser() as browser:
        page = await browser.newPage()
        await load_ticker_page(page, ticker)
        await load_dividends_table(page)
        html = await page.content()
        return cast(str, html)


def is_common(ticker: str) -> bool:
    """Определяет является ли акция обыкновенной."""
    if len(ticker) == COMMON_TICKER_LENGTH:
        return True
    elif len(ticker) == COMMON_TICKER_LENGTH + 1:
        if ticker[COMMON_TICKER_LENGTH] == PREFERRED_TICKER_ENDING:
            return False
    raise ports.DataError(f"Некорректный тикер {ticker}")


def get_col_desc(ticker: str) -> List[parser.ColDesc]:
    """Формирует список с описанием необходимых столбцов."""
    date = parser.ColDesc(
        num=5,
        raw_name=("E", "Дата закрытия реестра акционеров", "Под выплату дивидендов"),
        name=names.DATE,
        parser_func=parser.date_parser,
    )
    columns = [date]
    if is_common(ticker):
        common = parser.ColDesc(
            num=7,
            raw_name=("G", "Размер дивидендов", "АОИ"),
            name=ticker,
            parser_func=parser.div_parser,
        )
        columns.append(common)
        return columns
    preferred = parser.ColDesc(
        num=8, raw_name=("H", "Размер дивидендов", "АПИ"), name=ticker, parser_func=parser.div_parser,
    )
    columns.append(preferred)
    return columns


class ConomyUpdater(ports.AbstractUpdater):
    """Обновление для таблиц с дивидендами на https://www.conomy.ru/."""

    def __call__(self, name: ports.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        group, ticker = name
        if group != ports.CONOMY:
            raise ports.DataError(f"Некорректное имя таблицы для обновления {name}")
        logger.info(f"Загрузка данных: {name}")

        html = asyncio.run(get_html(ticker))
        cols_desc = get_col_desc(ticker)
        table = parser.HTMLTable(html, TABLE_INDEX, cols_desc)
        return table.get_df()
