"""Обновление данных с https://закрытияреестров.рф/."""
from typing import Final

import pandas as pd

from poptimizer.data.adapters.gateways import gateways
from poptimizer.data.adapters.html import description, parser
from poptimizer.shared import adapters, col

# Параметры парсинга сайта
URL: Final = "https://закрытияреестров.рф/"
BASE_TICKER_LENGTH: Final = 4
TABLE_INDEX: Final = 0


def _get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием необходимых столбцов."""
    date = description.ColDesc(
        num=0,
        raw_name=("Год за который производится выплата",),
        name=col.DATE,
        parser_func=description.date_parser,
    )
    columns = [date]

    if description.is_common(ticker):
        common = description.ColDesc(
            num=1,
            raw_name=("Дивиденд на одну обыкновенную акцию",),
            name=ticker,
            parser_func=description.div_parser,
        )
        columns.append(common)
        return columns

    preferred = description.ColDesc(
        num=2,
        raw_name=("Дивиденд на одну привилегированную акцию",),
        name=ticker,
        parser_func=description.div_parser,
    )
    columns.append(preferred)
    return columns


class CloseGateway(gateways.DivGateway):
    """Обновление данных с https://закрытияреестров.рф/."""

    _logger = adapters.AsyncLogger()

    async def __call__(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        cols_desc = _get_col_desc(ticker)
        base_ticker = ticker[:BASE_TICKER_LENGTH]
        url = f"{URL}{base_ticker}"
        try:
            df = await parser.get_df_from_url(url, TABLE_INDEX, cols_desc)
        except description.ParserError:
            return pd.DataFrame(columns=[ticker, col.CURRENCY])

        df[col.CURRENCY] = col.RUR
        return df
