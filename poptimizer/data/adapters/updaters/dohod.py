"""Обновление данных с https://dohod.ru."""
from typing import List

import pandas as pd

from poptimizer.data import names, ports
from poptimizer.data.adapters.updaters import connection, parser, updater

# Параметры парсинга сайта
URL = "https://www.dohod.ru/ik/analytics/dividend/"
TABLE_INDEX = 2


def get_col_desc(ticker: str) -> List[parser.ColDesc]:
    """Формирует список с описанием нужных столбцов."""
    date_col = parser.ColDesc(
        num=0,
        raw_name=("Дата закрытия реестра",),
        name=names.DATE,
        parser_func=parser.date_parser,
    )
    div_col = parser.ColDesc(
        num=2,
        raw_name=("Дивиденд (руб.)",),
        name=ticker,
        parser_func=parser.div_parser,
    )
    return [date_col, div_col]


class DohodUpdater(updater.BaseUpdater):
    """Обновление данных с https://dohod.ru."""

    def __call__(self, table_name: ports.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, ports.DOHOD)

        html = connection.get_html(f"{URL}{ticker.lower()}")
        cols_desc = get_col_desc(ticker)
        table = parser.HTMLTable(html, TABLE_INDEX, cols_desc)
        df = table.get_df()
        return df.sort_index(axis=0)
