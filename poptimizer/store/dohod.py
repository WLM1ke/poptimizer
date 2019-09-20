"""Менеджер данных по дивидендам с https://dohod.ru"""
from typing import Optional, Any, List, Dict

import requests

from poptimizer.config import POptimizerError
from poptimizer.store import parser
from poptimizer.store.db import DB
from poptimizer.store.manager import AbstractManager
from poptimizer.store.utils import DATE

# Наименование коллекции с данными
DOHOD = "dohod"

TABLE_INDEX = 2
HEADER_SIZE = 1


class Dohod(AbstractManager):
    """Информация о дивидендам с https://dohod.ru

    Каждый раз обновляется с нуля.
    """

    def __init__(self, db=DB) -> None:
        super().__init__(collection=DOHOD, db=db, create_from_scratch=True)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        url = f"https://www.dohod.ru/ik/analytics/dividend/{item.lower()}"
        with self._session.get(url) as respond:
            try:
                respond.raise_for_status()
            except requests.HTTPError:
                raise POptimizerError(f"Данные {url} не загружены")
            else:
                html = respond.text
        table = parser.HTMLTableParser(html, TABLE_INDEX)
        date_col = parser.DataColumn(
            DATE, 0, {0: "Дата закрытия реестра"}, parser.date_parser
        )
        div_col = parser.DataColumn(item, 2, {0: "Дивиденд (руб.)"}, parser.div_parser)
        columns = [date_col, div_col]
        data = table.get_formatted_data(columns, HEADER_SIZE)
        return sort_and_group(item, data)


def sort_and_group(item: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Сортирует по возрастанию и суммирует значения для одной даты."""
    rez = []
    for row in sorted(data, key=lambda x: x[DATE]):
        if not rez or row[DATE] != rez[-1][DATE]:
            rez.append(row)
        else:
            rez[-1][item] += row[item]
    return rez
