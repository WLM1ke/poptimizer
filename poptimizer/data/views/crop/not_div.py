"""Обрезка данных для различных источников кроме дивидендов."""
import functools
from typing import List, Tuple

import pandas as pd

from poptimizer.data_di.app import bootstrap, viewers
from poptimizer.data_di.domain.tables import base
from poptimizer.data_di.shared import col


def cpi(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Потребительская инфляция."""
    df = viewer.get_df(base.CPI, base.CPI)
    return df.loc[bootstrap.START_DATE :, col.CPI]  # type: ignore


def index(
    ticker: str = "MCFTRR",
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.Series:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR."""
    df = viewer.get_df(base.INDEX, ticker)
    return df.loc[bootstrap.START_DATE :, col.CLOSE]  # type: ignore


@functools.lru_cache(maxsize=1)
def quotes(
    tickers: Tuple[str, ...],
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> List[pd.DataFrame]:
    """Информация о котировках для заданных тикеров."""
    dfs = viewer.get_dfs(base.QUOTES, tickers)
    start_date = bootstrap.START_DATE
    return [df.loc[start_date:] for df in dfs]  # type: ignore
