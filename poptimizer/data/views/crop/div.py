"""Обрезка данных для различных источников по дивидендам."""
from typing import Tuple

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import bootstrap, viewers


def div_ext(
    ticker: str,
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Сводная информация из внешних источников по дивидендам."""
    df = viewer.get_df(ports.DIV_EXT, ticker)
    return df.loc[bootstrap.START_DATE :]  # type: ignore


def dividends(
    ticker: str,
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    df = viewer.get_df(ports.DIVIDENDS, ticker)
    return df.loc[bootstrap.START_DATE :]  # type: ignore


def dividends_all(
    tickers: Tuple[str, ...],
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Дивиденды по заданным тикерам после уплаты налогов.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.
    """
    dfs = viewer.get_dfs(ports.DIVIDENDS, tickers)
    dfs = [df.loc[bootstrap.START_DATE :] for df in dfs]  # type: ignore

    df = pd.concat(dfs, axis=1, sort=True)
    df = df.reindex(columns=tickers)
    df = df.fillna(0, axis=0)

    return df.mul(bootstrap.AFTER_TAX)
