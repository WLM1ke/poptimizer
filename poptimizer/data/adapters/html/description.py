"""Описание колонок для парсера html-таблиц."""
from datetime import datetime
from typing import Callable, Final, NamedTuple, Optional, Union

import pandas as pd

from poptimizer import config
from poptimizer.shared import col

# Параметры проверки обыкновенная акция или привилегированная
COMMON_TICKER_LENGTH: Final = 4
PREFERRED_TICKER_ENDING: Final = "P"


class ParserError(config.POptimizerError):
    """Ошибки в парсинге html-таблиц."""


def is_common(ticker: str) -> bool:
    """Определяет является ли акция обыкновенной."""
    if len(ticker) == COMMON_TICKER_LENGTH:
        return True
    elif len(ticker) == COMMON_TICKER_LENGTH + 1:
        if ticker[COMMON_TICKER_LENGTH] == PREFERRED_TICKER_ENDING:
            return False
    raise ParserError(f"Некорректный тикер {ticker}")


ParserFunc = Callable[[str], Union[None, float, datetime, str]]


class ColDesc(NamedTuple):
    """Описание столбца с данными.

    Используется для выбора определенных столбцов из html-таблицы, проверки ожидаемых значений в
    заголовках и преобразования из строк в нужный формат.

    - num: номер столбца
    - raw_name: часть исходного наименования для валидации
    - name: целевое наименование столбца
    - parser_func: функция для парсинга значений
    """

    num: int
    raw_name: tuple[str, ...]
    name: str
    parser_func: Optional[ParserFunc]


def reformat_df_with_cur(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Разделяет столбец на валюту и значение."""
    ticker_col = df[ticker]
    df[col.CURRENCY] = ticker_col.str.slice(start=-3)
    ticker_col = ticker_col.str.slice(stop=-3).str.strip()  # "27 "
    df[ticker] = pd.to_numeric(ticker_col)
    return df
