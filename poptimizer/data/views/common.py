"""Стандартные представления информации для остальных пакетов программы."""
import pandas as pd

from poptimizer.data import config
from poptimizer.data.app import handlers
from poptimizer.data.ports import base, col


def last_history_date() -> pd.Timestamp:
    """Последняя доступная дата исторических котировок."""
    table_name = base.TableName(base.TRADING_DATES, base.TRADING_DATES)
    df = handlers.get_df(table_name)
    return pd.Timestamp(df.loc[0, "till"])


def conomy(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с conomy.ru."""
    table_name = base.TableName(base.CONOMY, ticker)
    df = handlers.get_df(table_name)
    return df.loc[config.START_DATE :]  # type: ignore


def dohod(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с dohod.ru."""
    table_name = base.TableName(base.DOHOD, ticker)
    df = handlers.get_df(table_name)
    return df.loc[config.START_DATE :]  # type: ignore


def smart_lab() -> pd.DataFrame:
    """Информация по дивидендам с smart-lab.ru."""
    table_name = base.TableName(base.SMART_LAB, base.SMART_LAB)
    return handlers.get_df(table_name)


def dividends(ticker: str) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    table_name = base.TableName(base.DIVIDENDS, ticker)
    df = handlers.get_df(table_name)
    return df.loc[config.START_DATE :]  # type: ignore


def dividends_force_update(ticker: str) -> pd.DataFrame:
    """Дивиденды для данного тикера с принудительным обновлением данных по дивидендам."""
    table_name = base.TableName(base.DIVIDENDS, ticker)
    df = handlers.get_df(table_name)
    return df.loc[config.START_DATE :]  # type: ignore


def cpi(date: pd.Timestamp) -> pd.Series:
    """Потребительская инфляция."""
    table_name = base.TableName(base.CPI, base.CPI)
    df = handlers.get_df(table_name)
    return df.loc[config.START_DATE : date, col.CPI]  # type: ignore
