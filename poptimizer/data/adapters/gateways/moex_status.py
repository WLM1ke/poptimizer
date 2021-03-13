"""Данные о закрытии реестров https://www.moex.com."""
import re
from typing import Final, Optional, cast

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL = "https://www.moex.com/ru/listing/listing-register-closing.aspx"
TABLE_INDEX = 2

TICKER_PATTERN: Final = "[A-Z]+-RM"


def _ticker_parser(cell_text: str) -> Optional[str]:
    """Нахождение тикеров иностранных эмитентов."""
    re_div = re.search(TICKER_PATTERN, cell_text)
    if re_div:
        return re_div.group(0)
    return None


def get_col_desc() -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    ticker = description.ColDesc(
        num=0,
        raw_name=("Эмитент",),
        name=col.TICKER,
        parser_func=cast(parser.ParseFuncType, _ticker_parser),
    )
    date = description.ColDesc(
        num=2,
        raw_name=("Дата События",),
        name=col.DATE,
        parser_func=cell_parser.date_ru,
    )

    return [ticker, date]


class MOEXStatusGateway(gateways.DivStatusGateway):
    """Данные о закрытии реестров https://www.moex.com.

    Загружаются только данные по иностранным бумагам.
    """

    _logger = adapters.AsyncLogger()

    async def __call__(self) -> pd.DataFrame:
        """Получение ожидаемых дивидендов."""
        self._logger("Загрузка данных")

        cols_desc = get_col_desc()
        df = await parser.get_df_from_url(URL, TABLE_INDEX, cols_desc)
        return df.iloc[df.index.notnull()]
