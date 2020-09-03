"""Запросы содержащие обрезку по первоначальной дате."""
import pandas as pd

from poptimizer.data import config
from poptimizer.data.app import handlers
from poptimizer.data.ports import base, col


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


def dividends(ticker: str, force_update: bool = False) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    table_name = base.TableName(base.DIVIDENDS, ticker)
    df = handlers.get_df(table_name, force_update)
    return df.loc[config.START_DATE :]  # type: ignore


def cpi(date: pd.Timestamp) -> pd.Series:
    """Потребительская инфляция."""
    table_name = base.TableName(base.CPI, base.CPI)
    df = handlers.get_df(table_name)
    return df.loc[config.START_DATE : date, col.CPI]  # type: ignore


def index(last_date: pd.Timestamp) -> pd.DataFrame:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR.

    :param last_date:
        Последняя дата котировок.
    :return:
        История цен закрытия индекса.
    """
    table_name = base.TableName(base.INDEX, base.INDEX)
    df = handlers.get_df(table_name)
    return df.loc[config.START_DATE : last_date, col.CLOSE]  # type: ignore
