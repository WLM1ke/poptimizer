"""Обновление данных с https://www.streetinsider.com/."""
from typing import Optional

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import cell_parser, description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL = "https://www.streetinsider.com/dividend_history.php?q="
TABLE_INDEX = 0


def get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием нужных столбцов."""
    date_col = description.ColDesc(
        num=6,
        raw_name=("Rec. Date",),
        name=col.DATE,
        parser_func=cell_parser.date_us,
    )
    div_col = description.ColDesc(
        num=1,
        raw_name=("Amount",),
        name=ticker,
        parser_func=cell_parser.div_us,
    )
    return [date_col, div_col]


class StreetInsider(gateways.DivGateway):
    """Обновление данных с https://www.streetinsider.com/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> Optional[pd.DataFrame]:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        cols_desc = get_col_desc(ticker)
        international_ticker = ticker.lower()[:-3]
        url = f"{URL}{international_ticker}"
        try:
            df = await parser.get_df_from_url(url, TABLE_INDEX, cols_desc)
        except description.ParserError:
            return None

        df = self._sort_and_agg(df)
        df[col.CURRENCY] = col.USD

        return df
