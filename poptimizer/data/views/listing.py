"""Функции предоставления данных о торгуемых бумагах."""
import functools
from typing import Optional

import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import bootstrap, viewers
from poptimizer.data.domain import events
from poptimizer.data.views import quotes
from poptimizer.shared import col


def last_history_date(
    viewer: viewers.Viewer = bootstrap.VIEWER,
    bus: bootstrap.TableBus = bootstrap.BUS,
) -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    event = events.DateCheckRequired()
    bus.handle_event(event)
    df = viewer.get_df(ports.TRADING_DATES, ports.TRADING_DATES)
    return df.loc[0, "till"]


def all_history_date(
    tickers: tuple[str, ...],
    *,
    start: Optional[pd.Timestamp] = None,
    end: Optional[pd.Timestamp] = None,
    bus: bootstrap.TableBus = bootstrap.BUS,
) -> pd.Index:
    """Перечень дат для которых есть котировки.

    Может быть ограничен сверху или снизу.
    """
    event = events.DateCheckRequired()
    bus.handle_event(event)

    return quotes.all_prices(tickers).loc[start:end].index


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
