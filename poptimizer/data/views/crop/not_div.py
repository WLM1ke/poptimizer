"""Обрезка данных для различных источников кроме дивидендов."""
import functools
from typing import List, Tuple

import pandas as pd

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import col, outer


def cpi() -> pd.Series:
    """Потребительская инфляция."""
    table_name = outer.TableName(outer.CPI, outer.CPI)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    start_date = bootstrap.get_start_date()
    return df.loc[start_date:, col.CPI]  # type: ignore


def index(ticker: str = "MCFTRR") -> pd.Series:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR."""
    table_name = outer.TableName(outer.INDEX, ticker)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    start_date = bootstrap.get_start_date()
    return df.loc[start_date:, col.CLOSE]  # type: ignore


@functools.lru_cache(maxsize=1)
def quotes(tickers: Tuple[str, ...]) -> List[pd.DataFrame]:
    """Информация о котировках для заданных тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Список с котировками.
    """
    group: outer.GroupName = outer.QUOTES
    requests_handler = bootstrap.get_handler()
    dfs = requests_handler.get_dfs(group, tickers)
    start_date = bootstrap.get_start_date()
    return [df.loc[start_date:] for df in dfs]  # type: ignore
