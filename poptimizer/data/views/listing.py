"""Функции предоставления данных о торгуемых бумагах."""
from typing import Tuple

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.shared import col


def last_history_date(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    df = viewer.get_df(ports.TRADING_DATES, ports.TRADING_DATES)
    return df.loc[0, "till"]


def securities(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Index:
    """Все акции."""
    df = viewer.get_df(ports.SECURITIES, ports.SECURITIES)
    return df.index


def ticker_types(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Типы ценных бумаг."""
    df = viewer.get_df(ports.SECURITIES, ports.SECURITIES)
    return df[col.TICKER_TYPE]


def lot_size(tickers: Tuple[str, ...], viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Информация о размере лотов для тикеров."""
    df = viewer.get_df(ports.SECURITIES, ports.SECURITIES)
    return df.loc[list(tickers), col.LOT_SIZE]
