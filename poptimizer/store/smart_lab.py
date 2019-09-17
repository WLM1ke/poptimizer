"""Менеджер данных по предстоящим дивидендам с https://www.smart-lab.ru"""
from typing import Optional, Any, List, Dict

import requests

from poptimizer.config import POptimizerError
from poptimizer.store import parser
from poptimizer.store.manager_new import AbstractManager
from poptimizer.store.utils_new import DATE, TICKER, DIVIDENDS, DB, MISC

# Наименование данных в коллекции MISC
SMART_LAB = "smart-lab"

# Параметры парсинга сайта
URL = "https://smart-lab.ru/dividends/index/order_by_t2_date/asc/"
TABLE_INDEX = 1
HEADER_SIZE = 1
FOOTER_SIZE = 1

TICKER_COLUMN = parser.DataColumn(
    TICKER,
    1,
    {0: "Тикер", -1: "\n+добавить дивиденды\nИстория выплаченных дивидендов\n"},
    lambda x: x,
)

DATE_COLUMN = parser.DataColumn(
    DATE,
    4,
    {0: "дата отсечки", -1: "\n+добавить дивиденды\nИстория выплаченных дивидендов\n"},
    parser.date_parser,
)

DIVIDENDS_COLUMN = parser.DataColumn(
    DIVIDENDS,
    7,
    {0: "дивиденд,руб", -1: "\n+добавить дивиденды\nИстория выплаченных дивидендов\n"},
    parser.div_parser,
)


class SmartLab(AbstractManager):
    """Информация о ближайших дивидендах на https://www.smart-lab.ru

    Каждый раз обновляется с нуля.
    """

    def __init__(self, db=DB) -> None:
        super().__init__(
            collection=MISC, db=db, create_from_scratch=True, unique_index=False
        )

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        if item != SMART_LAB:
            raise POptimizerError(
                f"Отсутствуют данные {self._collection.full_name}.{item}"
            )
        with self._session.get(URL) as respond:
            try:
                respond.raise_for_status()
            except requests.HTTPError:
                raise POptimizerError(f"Данные {URL} не загружены")
            else:
                html = respond.text
        table = parser.HTMLTableParser(html, TABLE_INDEX)
        columns = [TICKER_COLUMN, DATE_COLUMN, DIVIDENDS_COLUMN]
        return table.get_formatted_data(columns, HEADER_SIZE, FOOTER_SIZE)
