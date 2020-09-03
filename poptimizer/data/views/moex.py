"""Функции предоставления данных по котировкам акций."""
from typing import Tuple

import pandas as pd

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import base, col


def last_history_date() -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    table_name = base.TableName(base.TRADING_DATES, base.TRADING_DATES)
    df = bootstrap.get_handler().get_df(table_name)
    return pd.Timestamp(df.loc[0, "till"])


def securities_with_reg_number() -> pd.Index:
    """Все акции с регистрационным номером."""
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    df = bootstrap.get_handler().get_df(table_name)
    return df.dropna(axis=0).index


def lot_size(tickers: Tuple[str, ...]) -> pd.Series:
    """Информация о размере лотов для тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Информация о размере лотов.
    """
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    df = bootstrap.get_handler().get_df(table_name)
    return df.loc[list(tickers), col.LOT_SIZE]
