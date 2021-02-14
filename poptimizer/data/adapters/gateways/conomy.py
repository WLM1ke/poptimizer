"""Загрузка данных с https://www.conomy.ru/."""
import asyncio
from typing import Final, cast

import pandas as pd
from pyppeteer import errors
from pyppeteer.page import Page

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import chromium, description, parser
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
    page = await browser.get_new_page()
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

    async def __call__(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        try:
            # На некоторых компьютерах/операционных системах Chromium перестает реагировать на команды
            # Поэтому загрузка принудительно приостанавливается
            html = await asyncio.wait_for(_get_html(ticker), timeout=CHROMIUM_TIMEOUT)
        except (errors.TimeoutError, asyncio.exceptions.TimeoutError):
            return pd.DataFrame(columns=[ticker, col.CURRENCY])
        cols_desc = _get_col_desc(ticker)
        df = parser.get_df_from_html(html, TABLE_INDEX, cols_desc)
        df = df.dropna()

        df = self._sort_and_agg(df)
        df[col.CURRENCY] = col.RUR
        return df
