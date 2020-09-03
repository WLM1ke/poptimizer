"""Стандартные представления информации для остальных пакетов программы."""
import pandas as pd

from poptimizer.data.app import handlers
from poptimizer.data.ports import base


def last_history_date() -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    table_name = base.TableName(base.TRADING_DATES, base.TRADING_DATES)
    df = handlers.get_df(table_name)
    return pd.Timestamp(df.loc[0, "till"])
