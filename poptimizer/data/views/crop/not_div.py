"""Обрезка данных для различных источников кроме дивидендов."""
import functools

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.shared import col


def cpi(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Потребительская инфляция."""
    df = viewer.get_df(ports.CPI, ports.CPI)
    return df.loc[bootstrap.START_DATE :, col.CPI]  # type: ignore


def index(
    ticker: str = "MCFTRR",
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.Series:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR."""
    df = viewer.get_df(ports.INDEX, ticker)
    return df.loc[bootstrap.START_DATE :, col.CLOSE]  # type: ignore


def usd(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Курс доллара."""
    df = viewer.get_df(ports.USD, ports.USD)
    return df.loc[bootstrap.START_DATE :, col.CLOSE]  # type: ignore


@functools.lru_cache(maxsize=1)
def quotes(
    tickers: tuple[str, ...],
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> list[pd.DataFrame]:
    """Информация о котировках для заданных тикеров."""
    dfs = viewer.get_dfs(ports.QUOTES, tickers)
    start_date = bootstrap.START_DATE
    return [df.loc[start_date:] for df in dfs]  # type: ignore
