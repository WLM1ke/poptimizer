"""Загрузка данных со https://www.smart-lab.ru."""
import pandas as pd

from poptimizer.data_di.adapters.html import description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL = "https://smart-lab.ru/dividends/index/order_by_cut_off_date/asc/"
TABLE_INDEX = 0
HEADER_SIZE = 1
FOOTER = "+добавить дивиденды"


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
        parser_func=description.date_parser,
    )
    div = description.ColDesc(
        num=5,
        raw_name=("дивиденд,руб",),
        name=col.DIVIDENDS,
        parser_func=description.div_parser,
    )
    return [ticker, date, div]


class SmartLabGateway:
    """Обновление данных с https://www.smart-lab.ru."""

    _logger = adapters.AsyncLogger()

    async def get(self) -> pd.DataFrame:
        """Получение ожидаемых дивидендов."""
        self._logger("Загрузка данных")

        cols_desc = get_col_desc()
        df = await parser.get_df_from_url(URL, TABLE_INDEX, cols_desc)
        if FOOTER not in df.index[-1]:
            raise description.ParserError("Некорректная html-таблица")
        return df.dropna()
