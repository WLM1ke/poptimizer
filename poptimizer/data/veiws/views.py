"""Стандартные представления информации для остальных пакетов программы."""
import pandas as pd

from poptimizer.data import ports
from poptimizer.data.app import config, handlers


def last_history_date() -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    table_name = ports.TableName(ports.TRADING_DATES, ports.TRADING_DATES)
    app_config = config.get()
    df = handlers.get_table(table_name, app_config)
    return pd.Timestamp(df.loc[0, "till"])


def conomy(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с conomy.ru."""
    table_name = ports.TableName(ports.CONOMY, ticker)
    app_config = config.get()
    return handlers.get_table(table_name, app_config)
