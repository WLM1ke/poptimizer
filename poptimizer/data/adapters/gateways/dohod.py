"""Обновление данных с https://dohod.ru."""
from typing import Optional

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL = "https://www.dohod.ru/ik/analytics/dividend/"
TABLE_INDEX = 2


def get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=1,
        raw_name=("Дата закрытия реестра",),
        name=col.DATE,
        parser_func=cell_parser.date_ru,
    )
    div_col = description.ColDesc(
        num=3,
        raw_name=("Дивиденд",),
        name=ticker,
        parser_func=cell_parser.div_ru,
    )
    return [date_col, div_col]


class DohodGateway(gateways.DivGateway):
    """Обновление данных с https://dohod.ru."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> Optional[pd.DataFrame]:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        cols_desc = get_col_desc(ticker)
        url = f"{URL}{ticker.lower()}"
        try:
            df = await parser.get_df_from_url(url, TABLE_INDEX, cols_desc)
        except description.ParserError:
            return None

        df = self._sort_and_agg(df)
        df[col.CURRENCY] = col.RUR
        return df
