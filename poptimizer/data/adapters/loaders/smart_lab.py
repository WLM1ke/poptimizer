"""Загрузка данных со https://www.smart-lab.ru."""
import pandas as pd

from poptimizer.data.adapters import logger
from poptimizer.data.adapters.html import description, parser
from poptimizer.data.ports import col, outer

# Параметры парсинга сайта
URL = "https://smart-lab.ru/dividends/index/order_by_cut_off_date/asc/"
TABLE_INDEX = 0
HEADER_SIZE = 1
FOOTER = "+добавить дивиденды"


def get_col_desc() -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    ticker = description.ColDesc(num=1, raw_name=("Тикер",), name=col.TICKER, parser_func=None)
    date = description.ColDesc(
        num=9,
        raw_name=("дата отсечки",),
        name=col.DATE,
        parser_func=description.date_parser,
    )
    div = description.ColDesc(
        num=5,
        raw_name=("дивиденд,руб",),
        name=col.DIVIDENDS,
        parser_func=description.div_parser,
    )
    return [ticker, date, div]


class SmartLabLoader(logger.LoaderLoggerMixin, outer.AbstractLoader):
    """Обновление данных с https://www.smart-lab.ru."""

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        name = self._log_and_validate_group(table_name, outer.SMART_LAB)
        if name != outer.SMART_LAB:
            raise outer.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        cols_desc = get_col_desc()
        df = await parser.get_df_from_url(URL, TABLE_INDEX, cols_desc)
        if FOOTER not in df.index[-1]:
            raise outer.DataError(f"Некорректная html-таблица {table_name}")
        return df.dropna()
