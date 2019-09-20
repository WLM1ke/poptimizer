"""Менеджер данных по дивидендам с https://www.conomy.ru/"""
import asyncio
from typing import Optional, Any, List, Dict

import pyppeteer
from pyppeteer.page import Page

from poptimizer.config import POptimizerError
from poptimizer.store import parser, dohod
from poptimizer.store.database import DB
from poptimizer.store.manager import AbstractManager
from poptimizer.store.utils import DATE

# Наименование коллекции с данными
CONOMY = "conomy"

# Параметры поиска страницы эмитента
SEARCH_URL = "https://www.conomy.ru/search"
SEARCH_FIELD = '//*[@id="issuer_search"]'

# Параметры поиска данных по дивидендам
DIVIDENDS_MENU = '//*[@id="page-wrapper"]/div/nav/ul/li[5]/a'
DIVIDENDS_TABLE = '//*[@id="page-container"]/div[2]/div/div[1]'

# Параметры парсинга таблицы с дивидендами
TABLE_INDEX = 1
HEADER_SIZE = 3

# Параметры проверки обыкновенная акция или привилегированная
COMMON_TICKER_LENGTH = 4
PREFERRED_TICKER_ENDING = "P"


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
    """Возвращает html-код страницы с данными по дивидендам с сайта https://www.conomy.ru/"""
    browser = await pyppeteer.launch()
    try:
        page = await browser.newPage()
        await load_ticker_page(page, ticker)
        await load_dividends_table(page)
        html = await page.content()
    finally:
        await browser.close()
    return html


def is_common(ticker: str) -> bool:
    """Определяет является ли акция обыкновенной."""
    if len(ticker) == COMMON_TICKER_LENGTH:
        return True
    elif (
        len(ticker) == COMMON_TICKER_LENGTH + 1
        and ticker[COMMON_TICKER_LENGTH] == PREFERRED_TICKER_ENDING
    ):
        return False
    raise POptimizerError(f"Некорректный тикер {ticker}")


class Conomy(AbstractManager):
    """Информация о дивидендам с https://www.conomy.ru/

    Каждый раз обновляется с нуля.
    """

    def __init__(self, db=DB) -> None:
        super().__init__(collection=CONOMY, db=db, create_from_scratch=True)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        while True:
            try:
                html = asyncio.run(get_html(item))
            except asyncio.TimeoutError:
                continue
            else:
                break
        # noinspection PyUnboundLocalVariable
        table = parser.HTMLTableParser(html, TABLE_INDEX)
        date_column = parser.DataColumn(
            DATE,
            5,
            {1: "Дата закрытия реестра акционеров", 2: "Под выплату дивидендов"},
            parser.date_parser,
        )
        columns = [date_column]
        common_column = parser.DataColumn(
            item, 7, {1: "Размер дивидендов", 2: "АОИ"}, parser.div_parser
        )
        preferred_column = parser.DataColumn(
            item, 8, {1: "Размер дивидендов", 2: "АПИ"}, parser.div_parser
        )
        if is_common(item):
            columns.append(common_column)
        else:
            columns.append(preferred_column)
        data = table.get_formatted_data(columns, HEADER_SIZE)
        data = [row for row in data if row[DATE] is not None]
        return dohod.sort_and_group(item, data)
