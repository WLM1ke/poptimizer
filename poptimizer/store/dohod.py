"""Менеджер данных по дивидендам с https://dohod.ru"""
from typing import Union, Tuple

import aiohttp

from poptimizer.config import POptimizerError
from poptimizer.store import parser
from poptimizer.store.manager import AbstractManager
from poptimizer.store.utils import DATE

# Данные  хранятся в отдельной базе
CATEGORY_DOHOD = "dohod"

TABLE_INDEX = 2
HEADER_SIZE = 1

DATE_COLUMN = parser.DataColumn(0, {0: "Дата закрытия реестра"}, parser.date_parser)

DIVIDENDS_COLUMN = parser.DataColumn(2, {0: "Дивиденд (руб.)"}, parser.div_parser)


class Dohod(AbstractManager):
    """Информация о дивидендам с https://dohod.ru

    Каждый раз обновляется с нуля.
    """

    CREATE_FROM_SCRATCH = True

    def __init__(self, ticker: Union[str, Tuple[str, ...]]):
        super().__init__(ticker, CATEGORY_DOHOD)

    async def _download(self, name: str):
        url = f"https://www.dohod.ru/ik/analytics/dividend/{name.lower()}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError:
                    raise POptimizerError(f"Данные {url} не загружены")
                else:
                    html = await resp.text()
        table = parser.HTMLTableParser(html, TABLE_INDEX)
        columns = [DATE_COLUMN, DIVIDENDS_COLUMN]
        df = table.make_df(columns, HEADER_SIZE)
        df.columns = [DATE, name]
        df.set_index(DATE, inplace=True)
        df.sort_index(inplace=True)
        return df[name]
