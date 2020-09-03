"""Функции предоставления данных по котировкам акций."""
from typing import Tuple

import pandas as pd

from poptimizer.data.app import handlers
from poptimizer.data.ports import base, col


def securities_with_reg_number() -> pd.Index:
    """Все акции с регистрационным номером."""
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    df = handlers.get_df(table_name)
    return df.dropna(axis=0).index


def lot_size(tickers: Tuple[str, ...]) -> pd.Series:
    """Информация о размере лотов для тикеров.

    :param tickers:
        Перечень тикеров, для которых нужна информация.
    :return:
        Информация о размере лотов.
    """
    table_name = base.TableName(base.SECURITIES, base.SECURITIES)
    df = handlers.get_df(table_name)
    return df.loc[list(tickers), col.LOT_SIZE]
