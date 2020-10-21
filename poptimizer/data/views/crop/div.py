"""Обрезка данных для различных источников по дивидендам."""
from typing import Tuple

import pandas as pd

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import outer


def conomy(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с conomy.ru."""
    table_name = outer.TableName(outer.CONOMY, ticker)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    start_date = bootstrap.get_start_date()
    return df.loc[start_date:]  # type: ignore


def bcs(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с bcs-express.ru."""
    table_name = outer.TableName(outer.BCS, ticker)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    start_date = bootstrap.get_start_date()
    return df.loc[start_date:]  # type: ignore


def dohod(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с dohod.ru."""
    table_name = outer.TableName(outer.DOHOD, ticker)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    start_date = bootstrap.get_start_date()
    return df.loc[start_date:]  # type: ignore


def dividends(ticker: str, force_update: bool = False) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    table_name = outer.TableName(outer.DIVIDENDS, ticker)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name, force_update)
    start_date = bootstrap.get_start_date()
    return df.loc[start_date:]  # type: ignore


def dividends_all(tickers: Tuple[str, ...]) -> pd.DataFrame:
    """Дивиденды по заданным тикерам после уплаты налогов.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.

    :param tickers:
        Тикеры, для которых нужна информация.
    :return:
        Дивиденды.
    """
    group: outer.GroupName = outer.DIVIDENDS
    requests_handler = bootstrap.get_handler()
    dfs = requests_handler.get_dfs(group, tickers)

    start_date = bootstrap.get_start_date()
    dfs = [df.loc[start_date:] for df in dfs]  # type: ignore

    df = pd.concat(dfs, axis=1)
    df = df.reindex(columns=tickers)
    df = df.fillna(0, axis=0)
    return df.mul(bootstrap.get_after_tax_rate())
