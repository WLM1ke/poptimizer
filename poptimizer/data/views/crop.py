"""Запросы содержащие обрезку по первоначальной дате - для внутреннего использования."""
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


def cpi() -> pd.Series:
    """Потребительская инфляция."""
    table_name = base.TableName(base.CPI, base.CPI)
    df = bootstrap.get_handler().get_df(table_name)
    return df.loc[bootstrap.get_start_date() :, col.CPI]  # type: ignore


def index() -> pd.DataFrame:
    """Загрузка данных по индексу полной доходности с учетом российских налогов - MCFTRR."""
    table_name = base.TableName(base.INDEX, base.INDEX)
    df = bootstrap.get_handler().get_df(table_name)
    return df.loc[bootstrap.get_start_date() :, col.CLOSE]  # type: ignore
