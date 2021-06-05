"""Загрузка максимальной процентной ставке в крупнейших банках."""
import re
from datetime import datetime
from typing import Final, Optional

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL: Final = "https://www.cbr.ru/statistics/avgprocstav/"
TABLE_INDEX: Final = 0
DATE_PATTERN: Final = r"I{1,3}\.\d{2}\.\d{4}"


def date_parser(date: str) -> Optional[datetime]:
    """Функция парсинга значений в столбце с датами закрытия реестра."""
    re_date = re.search(DATE_PATTERN, date)
    if re_date:
        dec, month, year = re_date.group(0).split(".")
        day = (len(dec) - 1) * 10 + 1
        return datetime(int(year), int(month), day)
    return None


def get_col_desc() -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=0,
        raw_name=("Декада",),
        name=col.DATE,
        parser_func=date_parser,
    )
    div_col = description.ColDesc(
        num=1,
        raw_name=("Ставка",),
        name=col.RF,
        parser_func=cell_parser.div_ru,
    )
    return [date_col, div_col]


class RFGateway(gateways.BaseGateway):
    """Обновление о безрисковой ставке с https://www.cbr.ru/statistics/avgprocstav/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self) -> Optional[pd.DataFrame]:
        """Получение таблицы со ставками."""
        self._logger("Загрузка данных")

        cols_desc = get_col_desc()
        df = await parser.get_df_from_url(URL, TABLE_INDEX, cols_desc)

        return df.div(100).sort_index(axis=0)
