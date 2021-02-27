"""Загрузка данных со https://www.smart-lab.ru."""
import pandas as pd

from poptimizer.data.adapters.html import cell_parser, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL = "https://smart-lab.ru/dividends/index/order_by_yield/desc/"
TABLE_INDEX = 0
HEADER_SIZE = 1


def get_col_desc() -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    ticker = description.ColDesc(
        num=1,
        raw_name=("Тикер",),
        name=col.TICKER,
        parser_func=None,
    )
    date = description.ColDesc(
        num=9,
        raw_name=("дата отсечки",),
        name=col.DATE,
        parser_func=cell_parser.date_ru,
    )
    div = description.ColDesc(
        num=5,
        raw_name=("дивиденд,руб",),
        name=col.DIVIDENDS,
        parser_func=cell_parser.div_ru,
    )
    return [ticker, date, div]


class SmartLabGateway:
    """Обновление данных с https://www.smart-lab.ru."""

    _logger = adapters.AsyncLogger()

    async def __call__(self) -> pd.DataFrame:
        """Получение ожидаемых дивидендов."""
        self._logger("Загрузка данных")

        cols_desc = get_col_desc()
        df = await parser.get_df_from_url(URL, TABLE_INDEX, cols_desc)
        return df.dropna()
