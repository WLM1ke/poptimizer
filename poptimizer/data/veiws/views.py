"""Стандартные представления информации для остальных пакетов программы."""
import pandas as pd

from poptimizer.data.core.app import requests


def last_history_date() -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    df = requests.get_table(("trading_dates", "trading_dates"))
    return pd.Timestamp(df.loc[0, "till"])
