"""Обновление данных с https://dohod.ru."""
import pandas as pd

from poptimizer.data.adapters import logger
from poptimizer.data.adapters.html import description, parser
from poptimizer.data.ports import outer
from poptimizer.shared import col

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


class DohodLoader(logger.LoaderLoggerMixin, outer.AbstractLoader):
    """Обновление данных с https://dohod.ru."""

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, outer.DOHOD)

        cols_desc = get_col_desc(ticker)
        url = f"{URL}{ticker.lower()}"
        try:
            df = await parser.get_df_from_url(url, TABLE_INDEX, cols_desc)
        except outer.DataError:
            return pd.DataFrame(columns=[ticker])
        df = df.sort_index(axis=0)
        return df.groupby(lambda date: date).sum()
