"""Обрезка данных для различных источников по дивидендам."""
from typing import Tuple

import pandas as pd

import poptimizer.data.ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.data.domain import events


def div_ext(
    ticker: str,
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Сводная информация из внешних источников по дивидендам."""
    df = viewer.get_df(poptimizer.data.ports.DIV_EXT, ticker)
    return df.loc[bootstrap.START_DATE :]  # type: ignore


def dividends(
    ticker: str,
    force_update: bool = False,
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    if force_update:
        command = events.UpdateDivCommand(ticker)
        bootstrap.BUS.handle_event(command)
    df = viewer.get_df(poptimizer.data.ports.DIVIDENDS, ticker)
    return df.loc[bootstrap.START_DATE :]  # type: ignore


def dividends_all(
    tickers: Tuple[str, ...],
    viewer: viewers.Viewer = bootstrap.VIEWER,
) -> pd.DataFrame:
    """Дивиденды по заданным тикерам после уплаты налогов.

    Значения для дат, в которые нет дивидендов у данного тикера (есть у какого-то другого),
    заполняются 0.
    """
    dfs = viewer.get_dfs(poptimizer.data.ports.DIVIDENDS, tickers)
    dfs = [df.loc[bootstrap.START_DATE :] for df in dfs]  # type: ignore

    df = pd.concat(dfs, axis=1)
    df = df.reindex(columns=tickers)
    df = df.fillna(0, axis=0)
    return df.mul(bootstrap.AFTER_TAX)
