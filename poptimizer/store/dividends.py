"""Менеджер данных для дивидендов."""
import sqlite3
from typing import Tuple

import pandas as pd
from pandas.io.sql import DatabaseError

from poptimizer.config import DATA_PATH
from poptimizer.store.manager import AbstractManager

# Данные по дивидендам хранятся во вложенной базе
from poptimizer.store.utils import DATE

CATEGORY_DIVIDENDS = "dividends"

# База содержит данные с начала 2010 года
DIVIDENDS_START = pd.Timestamp("2010-01-01")

SQLITE = str(DATA_PATH / "dividends.db")


class Dividends(AbstractManager):
    """Дивиденды и время закрытия реестра для акций."""

    CREATE_FROM_SCRATCH = True

    def __init__(self, tickers: Tuple[str, ...]):
        super().__init__(tickers, CATEGORY_DIVIDENDS)

    async def _download(self, name: str):
        """Загружает полностью данные по дивидендам.

        Загрузка осуществляется из обновляемой в ручную SQLite базы данных по дивидендам."""
        con = sqlite3.connect(SQLITE)
        query = f"SELECT DATE, DIVIDENDS FROM {name}"
        try:
            df = pd.read_sql_query(query, con, index_col=DATE, parse_dates=[DATE])
        except DatabaseError:
            con.close()
            return pd.Series(name=name, index=pd.DatetimeIndex([], name=DATE))
        else:
            con.close()
            df = df[df.index >= DIVIDENDS_START]
            # Несколько выплат в одну дату объединяются
            df = df.groupby(DATE).sum()
            df.columns = [name]
            return df[name]
