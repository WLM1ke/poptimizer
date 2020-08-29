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


def dohod(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с dohod.ru."""
    table_name = ports.TableName(ports.DOHOD, ticker)
    app_config = config.get()
    return handlers.get_table(table_name, app_config)


def smart_lab() -> pd.DataFrame:
    """Информация по дивидендам с smart-lab.ru."""
    table_name = ports.TableName(ports.SMART_LAB, ports.SMART_LAB)
    app_config = config.get()
    return handlers.get_table(table_name, app_config)


def dividends(ticker: str) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    table_name = ports.TableName(ports.DIVIDENDS, ticker)
    app_config = config.get()
    return handlers.get_table(table_name, app_config)


def dividends_force_update(ticker: str) -> pd.DataFrame:
    """Дивиденды для данного тикера с принудительным обновлением данных по дивидендам."""
    table_name = ports.TableName(ports.DIVIDENDS, ticker)
    app_config = config.get()
    return handlers.get_table_force_update(table_name, app_config)
