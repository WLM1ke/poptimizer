"""Обновление данных с https://investmint.ru/."""
import re
import types
from datetime import datetime
from typing import Final, Optional

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL: Final = "https://investmint.ru/"
DATE_PATTERN: Final = r"(\d{1,2})\s(\S{3})\s(\d{4})"
MONTHS_NAMES: Final = types.MappingProxyType(
    {
        "янв": 1,
        "фев": 2,
        "мар": 3,
        "апр": 4,
        "мая": 5,
        "июн": 6,
        "июл": 7,
        "авг": 8,
        "сен": 9,
        "окт": 10,
        "ноя": 11,
        "дек": 12,
    },
)


def _date_parser(date: str) -> Optional[datetime]:
    """Функция парсинга значений в столбце с датами закрытия реестра."""
    re_date = re.search(DATE_PATTERN, date)
    if re_date:
        return datetime(
            year=int(re_date.group(3)),
            month=MONTHS_NAMES[re_date.group(2)],
            day=int(re_date.group(1)),
        )
    return None


def get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=2,
        raw_name=("Реестр",),
        name=col.DATE,
        parser_func=_date_parser,
    )
    div_col = description.ColDesc(
        num=5,
        raw_name=("Дивиденд",),
        name=ticker,
        parser_func=description.div_parser_with_cur,
    )
    return [date_col, div_col]


class InvestMintGateway(gateways.DivGateway):
    """Обновление данных с https://investmint.ru/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        cols_desc = get_col_desc(ticker)
        url = f"{URL}{ticker.lower()}"
        try:
            html = await parser.get_html(url)
        except description.ParserError:
            return None

        table_index = 1
        if "Ближайшие дивиденды неизвестны" in html:
            table_index = 0

        try:
            df = parser.get_df_from_html(html, table_index, cols_desc)
        except description.ParserError:
            return None

        return description.reformat_df_with_cur(df, ticker)
