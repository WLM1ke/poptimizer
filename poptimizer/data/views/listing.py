"""Функции предоставления данных о торгуемых бумагах."""
import functools

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.data.domain import events
from poptimizer.shared import app, col


def last_history_date(
    viewer: viewers.Viewer = bootstrap.VIEWER,
    bus: app.EventBus = bootstrap.BUS,
) -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    event = events.AppStarted()
    bus.handle_event(event)
    df = viewer.get_df(ports.TRADING_DATES, ports.TRADING_DATES)
    return df.loc[0, "till"]


@functools.lru_cache(maxsize=1)
def _securities_info(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.DataFrame:
    """Сводная информация о торгуемых бумагах - кэшируется при первом вызове."""
    return viewer.get_df(ports.SECURITIES, ports.SECURITIES)


def securities(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Index:
    """Все акции."""
    df = _securities_info(viewer)
    return df.index


def ticker_types(viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Типы ценных бумаг."""
    df = _securities_info(viewer)
    return df[col.TICKER_TYPE]


def lot_size(tickers: tuple[str, ...], viewer: viewers.Viewer = bootstrap.VIEWER) -> pd.Series:
    """Информация о размере лотов для тикеров."""
    df = _securities_info(viewer)
    return df.loc[list(tickers), col.LOT_SIZE]
