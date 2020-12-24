"""Обновление данных с https://dohod.ru."""
import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL = "https://www.dohod.ru/ik/analytics/dividend/"
TABLE_INDEX = 2


def get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=0,
        raw_name=("Дата закрытия реестра",),
        name=col.DATE,
        parser_func=description.date_parser,
    )
    div_col = description.ColDesc(
        num=2,
        raw_name=("Дивиденд (руб.)",),
        name=ticker,
        parser_func=description.div_parser,
    )
    return [date_col, div_col]


class DohodGateway(gateways.DivGateway):
    """Обновление данных с https://dohod.ru."""

    _logger = adapters.AsyncLogger()

    async def get(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        cols_desc = get_col_desc(ticker)
        url = f"{URL}{ticker.lower()}"
        try:
            df = await parser.get_df_from_url(url, TABLE_INDEX, cols_desc)
        except description.ParserError:
            return pd.DataFrame(columns=[ticker])

        return df.groupby(lambda date: date).sum()
