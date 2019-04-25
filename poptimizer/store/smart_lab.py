"""Менеджер данных по предстоящим дивидендам с https://www.smart-lab.ru"""
import aiohttp
from aiohttp import ClientResponseError

from poptimizer.config import POptimizerError
from poptimizer.store import parser
from poptimizer.store.manager import AbstractManager
from poptimizer.store.utils import DIVIDENDS, TICKER, DATE

# Данные об ожидаемым дивидендам хранятся в основной базе
NAME_SMART_LAB = "smart-lab"

URL = "https://smart-lab.ru/dividends/index/order_by_yield/desc/"
TABLE_INDEX = 1
HEADER_SIZE = 1
FOOTER_SIZE = 1

TICKER_COLUMN = parser.DataColumn(
    1,
    {0: "Тикер", -1: "\n+добавить дивиденды\nИстория выплаченных дивидендов\n"},
    lambda x: x,
)

DATE_COLUMN = parser.DataColumn(
    4,
    {0: "дата отсечки", -1: "\n+добавить дивиденды\nИстория выплаченных дивидендов\n"},
    parser.date_parser,
)

DIVIDENDS_COLUMN = parser.DataColumn(
    7,
    {0: "дивиденд,руб", -1: "\n+добавить дивиденды\nИстория выплаченных дивидендов\n"},
    parser.div_parser,
)


class SmartLab(AbstractManager):
    """Информация о ближайших дивидендах на https://www.smart-lab.ru

    Каждый раз обновляется с нуля.
    """

    CREATE_FROM_SCRATCH = True
    IS_UNIQUE = False
    IS_MONOTONIC = False

    def __init__(self):
        super().__init__(NAME_SMART_LAB)

    async def _download(self, name: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as resp:
                try:
                    resp.raise_for_status()
                except ClientResponseError:
                    raise POptimizerError(f"Данные {URL} не загружены")
                else:
                    html = await resp.text()
        table = parser.HTMLTableParser(html, TABLE_INDEX)
        columns = [TICKER_COLUMN, DATE_COLUMN, DIVIDENDS_COLUMN]
        df = table.make_df(columns, HEADER_SIZE, FOOTER_SIZE)
        df.columns = [TICKER, DATE, DIVIDENDS]
        return df.set_index(DATE)
