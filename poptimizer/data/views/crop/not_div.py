"""Обрезка данных для различных источников кроме дивидендов."""
import functools
from typing import List, Tuple

import pandas as pd

import poptimizer.data.ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.shared import col


def cpi(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Потребительская инфляция."""
    df = viewer.get_df(poptimizer.data.ports.CPI, poptimizer.data.ports.CPI)
    return df.loc[bootstrap.START_DATE :, col.CPI]  # type: ignore


def index(
    ticker: str = "MCFTRR",
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.Series:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR."""
    df = viewer.get_df(poptimizer.data.ports.INDEX, ticker)
    return df.loc[bootstrap.START_DATE :, col.CLOSE]  # type: ignore


@functools.lru_cache(maxsize=1)
def quotes(
    tickers: Tuple[str, ...],
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> List[pd.DataFrame]:
    """Информация о котировках для заданных тикеров."""
    dfs = viewer.get_dfs(poptimizer.data.ports.QUOTES, tickers)
    start_date = bootstrap.START_DATE
    return [df.loc[start_date:] for df in dfs]  # type: ignore
