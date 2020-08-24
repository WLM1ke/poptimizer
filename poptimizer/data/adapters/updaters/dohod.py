"""Обновление данных с https://dohod.ru."""
from typing import List

import pandas as pd
import requests

from poptimizer.data import ports
from poptimizer.data.adapters import connection
from poptimizer.data.adapters.updaters import names, parser, updater
from poptimizer.data.ports import TableName

# Номер таблицы на странице
TABLE_INDEX = 2


def get_html(ticker: str) -> str:
    """Получает необходимую html-страницу с сайта https://dohod.ru."""
    url = f"https://www.dohod.ru/ik/analytics/dividend/{ticker.lower()}"
    session = connection.get_http_session()
    with session.get(url) as respond:
        try:
            respond.raise_for_status()
        except requests.HTTPError:
            raise ports.DataError(f"Данные {url} не загружены")
        else:
            html = respond.text
    return html


def get_col_desc(ticker: str) -> List[parser.ColDesc]:
    """Формирует список с описанием нужных столбцов."""
    date_col = parser.ColDesc(
        num=0, raw_name=("Дата закрытия реестра",), name=names.DATE, parser_func=parser.date_parser,
    )
    div_col = parser.ColDesc(
        num=2, raw_name=("Дивиденд (руб.)",), name=ticker, parser_func=parser.div_parser,
    )
    return [date_col, div_col]


class DohodUpdater(updater.BaseUpdater):
    """Обновление данных с https://dohod.ru."""

    def __call__(self, table_name: TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, ports.DOHOD)

        html = get_html(ticker)
        cols_desc = get_col_desc(ticker)
        table = parser.HTMLTable(html, TABLE_INDEX, cols_desc)
        return table.get_df()
