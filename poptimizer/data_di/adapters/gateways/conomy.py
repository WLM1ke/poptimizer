"""Загрузка данных с https://www.conomy.ru/."""
import asyncio
import atexit
import contextlib
from typing import Final, Optional, cast

import pandas as pd
import pyppeteer
from pyppeteer import browser, errors
from pyppeteer.page import Page

from poptimizer.data_di.adapters.gateways import gateways
from poptimizer.data_di.adapters.html import description, parser
from poptimizer.shared import adapters, col

# Параметры поиска страницы эмитента
SEARCH_URL: Final = "https://www.conomy.ru/search"
SEARCH_FIELD: Final = '//*[@id="issuer_search"]'

# Параметры поиска данных по дивидендам
DIVIDENDS_MENU: Final = '//*[@id="page-wrapper"]/div/nav/ul/li[5]/a'
DIVIDENDS_TABLE: Final = '//*[@id="page-container"]/div[2]/div/div[1]'

# Номер таблицы на html-странице и строки с заголовком
TABLE_INDEX: Final = 1

# Параметры проверки обыкновенная акция или привилегированная
COMMON_TICKER_LENGTH: Final = 4
PREFERRED_TICKER_ENDING: Final = "P"


class Browser:
    """Headless браузер, который запускается по необходимости."""

    def __init__(self) -> None:
        """Создает переменную для хранения браузера."""
        self._browser: Optional[browser.Browser] = None
        self._lock = asyncio.Lock()

    @contextlib.asynccontextmanager
    async def get_page(self) -> Page:
        """Контекстный менеджер, закрывающий страницу."""
        chromium = await self._load_browser()
        page = await chromium.newPage()
        try:
            yield page
        finally:
            await page.close()

    async def _load_browser(self) -> browser.Browser:
        """При необходимости загружает браузер и возвращает его."""
        async with self._lock:
            if self._browser is None:
                self._browser = await pyppeteer.launch(autoClose=False)
                atexit.register(self._close)
        return self._browser

    def _close(self) -> None:
        """Закрывает браузер."""
        if self._browser is not None:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._browser.close())


BROWSER: Final = Browser()


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


async def _get_html(ticker: str) -> str:
    """Возвращает html-код страницы с данными по дивидендам с сайта https://www.conomy.ru/."""
    async with BROWSER.get_page() as page:
        await _load_ticker_page(page, ticker)
        await _load_dividends_table(page)
        return cast(str, await page.content())


def _is_common(ticker: str) -> bool:
    """Определяет является ли акция обыкновенной."""
    if len(ticker) == COMMON_TICKER_LENGTH:
        return True
    elif len(ticker) == COMMON_TICKER_LENGTH + 1:
        if ticker[COMMON_TICKER_LENGTH] == PREFERRED_TICKER_ENDING:
            return False
    raise description.ParserError(f"Некорректный тикер {ticker}")


def _get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием необходимых столбцов."""
    date = description.ColDesc(
        num=5,
        raw_name=("E", "Дата закрытия реестра акционеров", "Под выплату дивидендов"),
        name=col.DATE,
        parser_func=description.date_parser,
    )
    columns = [date]

    if _is_common(ticker):
        common = description.ColDesc(
            num=7,
            raw_name=("G", "Размер дивидендов", "АОИ"),
            name=ticker,
            parser_func=description.div_parser,
        )
        columns.append(common)
        return columns

    preferred = description.ColDesc(
        num=8,
        raw_name=("H", "Размер дивидендов", "АПИ"),
        name=ticker,
        parser_func=description.div_parser,
    )
    columns.append(preferred)
    return columns


class ConomyGateway(gateways.DivGateway):
    """Обновление для таблиц с дивидендами на https://www.conomy.ru/."""

    _logger = adapters.AsyncLogger()

    async def get(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        try:
            html = await _get_html(ticker)
        except errors.TimeoutError:
            return pd.DataFrame(columns=[ticker])
        cols_desc = _get_col_desc(ticker)
        df = parser.get_df_from_html(html, TABLE_INDEX, cols_desc)
        df = df.dropna()
        return self._sort_and_agg(df)
