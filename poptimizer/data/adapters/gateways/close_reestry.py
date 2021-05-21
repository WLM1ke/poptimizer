"""Обновление данных с https://закрытияреестров.рф/."""
import re
from typing import Final, Optional

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL: Final = "https://закрытияреестров.рф/"
BASE_TICKER_LENGTH: Final = 4
TABLE_INDEX: Final = 0
DIV_PATTERN: Final = r"(.*\d)\s(\w{3})"


def parser_div(div: str) -> Optional[str]:
    """Функция парсинга значений в столбце с дивидендами."""
    re_div = re.search(DIV_PATTERN, div)
    if re_div:
        if re_div.group(2) == "руб":
            currency = col.RUR
        elif re_div.group(2) == "USD":
            currency = col.USD
        else:
            return None
        div_string = re_div.group(1) + currency
        div_string = div_string.replace(",", ".")
        return div_string.replace(" ", "")
    return None


def _get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием необходимых столбцов."""
    date = description.ColDesc(
        num=0,
        raw_name=("Год за который производится выплата",),
        name=col.DATE,
        parser_func=cell_parser.date_ru,
    )
    columns = [date]

    if description.is_common(ticker):
        common = description.ColDesc(
            num=1,
            raw_name=("Дивиденд на одну",),
            name=ticker,
            parser_func=parser_div,
        )
        columns.append(common)
        return columns

    preferred = description.ColDesc(
        num=2,
        raw_name=("Дивиденд на одну",),
        name=ticker,
        parser_func=parser_div,
    )
    columns.append(preferred)
    return columns


class CloseGateway(gateways.DivGateway):
    """Обновление данных с https://закрытияреестров.рф/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> Optional[pd.DataFrame]:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        cols_desc = _get_col_desc(ticker)
        base_ticker = ticker[:BASE_TICKER_LENGTH]
        url = f"{URL}{base_ticker}"
        try:
            df = await parser.get_df_from_url(url, TABLE_INDEX, cols_desc)
        except description.ParserError:
            return None

        raw_data = df[ticker]
        df[col.CURRENCY] = raw_data.str.slice(-3)
        df[ticker] = raw_data.str.slice(stop=-3).astype(float)

        return df
