"""Функции предоставления данных по котировкам акций."""
import functools
from typing import Tuple

import numpy as np
import pandas as pd

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import base, col
from poptimizer.data.views import crop


def last_history_date() -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    table_name = base.TableName(base.TRADING_DATES, base.TRADING_DATES)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    return pd.Timestamp(df.loc[0, "till"])


def securities_with_reg_number() -> pd.Index:
    """Все акции с регистрационным номером."""
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    return df.dropna(axis=0).index


def lot_size(tickers: Tuple[str, ...]) -> pd.Series:
    """Информация о размере лотов для тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Информация о размере лотов.
    """
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    requests_handler = bootstrap.get_handler()
    df = requests_handler.get_df(table_name)
    return df.loc[list(tickers), col.LOT_SIZE]


@functools.lru_cache(maxsize=1)
def prices(tickers: Tuple[str, ...], last_date: pd.Timestamp) -> pd.DataFrame:
    """Дневные цены закрытия для указанных тикеров до указанной даты включительно.

    Пропуски заполнены предыдущими значениями.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата цен закрытия.
    :return:
        Цены закрытия.
    """
    quotes_list = crop.quotes(tickers)
    df = pd.concat(
        [df[col.CLOSE] for df in quotes_list],
        axis=1,
    )
    df = df.loc[:last_date]
    df.columns = tickers
    return df.replace(to_replace=[np.nan, 0], method="ffill")


@functools.lru_cache(maxsize=1)
def turnovers(tickers: Tuple[str, ...], last_date: pd.Timestamp) -> pd.DataFrame:
    """Дневные обороты для указанных тикеров до указанной даты включительно.

    Пропуски заполнены нулевыми значениями.

    :param tickers:
        Тикеры, для которых нужна информация.
    :param last_date:
        Последняя дата оборотов.
    :return:
        Обороты.
    """
    quotes_list = crop.quotes(tickers)
    df = pd.concat(
        [df[col.TURNOVER] for df in quotes_list],
        axis=1,
    )
    df = df.loc[:last_date]
    df.columns = tickers
    return df.fillna(0, axis=0)
