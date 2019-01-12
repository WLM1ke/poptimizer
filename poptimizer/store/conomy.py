"""Менеджер данных по дивидендам с https://www.conomy.ru/"""
from typing import Union, Tuple

import pyppeteer

from poptimizer.config import POptimizerError
from poptimizer.store import parser
from poptimizer.store.manager import AbstractManager
from poptimizer.store.utils import DATE

# Данные  хранятся в отдельной базе
CATEGORY_CONOMY = "conomy"

# Параметры поиска страницы эмитента
SEARCH_URL = "https://www.conomy.ru/search"
SEARCH_FIELD = '//*[@id="issuer_search"]'

# Параметры поиска данных по дивидендам
DIVIDENDS_MENU = '//*[@id="page-wrapper"]/div/nav/ul/li[5]/a'
DIVIDENDS_TABLE = '//*[@id="page-container"]/div[2]/div/div[1]'

# Параметры парсинга таблицы с дивидендами
TABLE_INDEX = 1
HEADER_SIZE = 3

DATE_COLUMN = parser.DataColumn(
    5,
    {1: "Дата закрытия реестра акционеров", 2: "Под выплату дивидендов"},
    parser.date_parser,
)

COMMON_TICKER_LENGTH = 4
COMMON_COLUMN = parser.DataColumn(
    7, {1: "Размер дивидендов на \nодну акцию, руб.", 2: "АОИ"}, parser.div_parser
)
PREFERRED_TICKER_ENDING = "P"
PREFERRED_COLUMN = parser.DataColumn(
    8, {1: "Размер дивидендов на \nодну акцию, руб.", 2: "АПИ"}, parser.div_parser
)


async def load_ticker_page(page, ticker: str):
    """Вводит в поле поиска тикер и переходит на страницу с информацией по эмитенту."""
    await page.goto(SEARCH_URL)
    await page.waitForXPath(SEARCH_FIELD)
    element, *_ = await page.xpath(SEARCH_FIELD)
    await element.type(ticker)
    await element.press("Enter")


async def load_dividends_table(page):
    """Выбирает на странице эмитента меню дивиденды и дожидается загрузки таблиц с ними."""
    await page.waitForXPath(DIVIDENDS_MENU)
    element, *_ = await page.xpath(DIVIDENDS_MENU)
    await element.click()
    await page.waitForXPath(DIVIDENDS_TABLE)


async def get_html(ticker: str):
    """Возвращает html-код страницы с данными по дивидендам с сайта https://www.conomy.ru/"""

    try:
        browser = await pyppeteer.launch()
        page = await browser.newPage()
        await load_ticker_page(page, ticker)
        await load_dividends_table(page)
        html = await page.content()
    finally:
        await browser.close()
    return html


def is_common(ticker: str):
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

    CREATE_FROM_SCRATCH = True

    def __init__(self, ticker: Union[str, Tuple[str, ...]]):
        super().__init__(ticker, CATEGORY_CONOMY)

    async def _download(self, name: str):
        html = await get_html(name)
        table = parser.HTMLTableParser(html, TABLE_INDEX)
        columns = [DATE_COLUMN]
        if is_common(name):
            columns.append(COMMON_COLUMN)
        else:
            columns.append(PREFERRED_COLUMN)
        df = table.make_df(columns, HEADER_SIZE)
        df.dropna(inplace=True)
        df.columns = [DATE, name]
        df.set_index(DATE, inplace=True)
        df.sort_index(inplace=True)
        return df[name]
