"""Запросы содержащие обрезку по первоначальной дате."""
import pandas as pd

from poptimizer.data.config import bootstrap
from poptimizer.data.ports import base, col


def conomy(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с conomy.ru."""
    table_name = base.TableName(base.CONOMY, ticker)
    df = bootstrap.get_handler().get_df(table_name)
    return df.loc[bootstrap.get_start_date() :]  # type: ignore


def dohod(ticker: str) -> pd.DataFrame:
    """Информация по дивидендам с dohod.ru."""
    table_name = base.TableName(base.DOHOD, ticker)
    df = bootstrap.get_handler().get_df(table_name)
    return df.loc[bootstrap.get_start_date() :]  # type: ignore


def dividends(ticker: str, force_update: bool = False) -> pd.DataFrame:
    """Дивиденды для данного тикера."""
    table_name = base.TableName(base.DIVIDENDS, ticker)
    df = bootstrap.get_handler().get_df(table_name, force_update)
    return df.loc[bootstrap.get_start_date() :]  # type: ignore


def cpi(date: pd.Timestamp) -> pd.Series:
    """Потребительская инфляция."""
    table_name = base.TableName(base.CPI, base.CPI)
    df = bootstrap.get_handler().get_df(table_name)
    return df.loc[bootstrap.get_start_date() : date, col.CPI]  # type: ignore


def index(last_date: pd.Timestamp) -> pd.DataFrame:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR.

    :param last_date:
        Последняя дата котировок.
    :return:
        История цен закрытия индекса.
    """
    table_name = base.TableName(base.INDEX, base.INDEX)
    df = bootstrap.get_handler().get_df(table_name)
    return df.loc[bootstrap.get_start_date() : last_date, col.CLOSE]  # type: ignore
