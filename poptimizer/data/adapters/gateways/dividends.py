"""Загрузка основных данных по дивидендам."""
import pandas as pd
from pymongo import collection

from poptimizer import config
from poptimizer.data.adapters.gateways import gateways
from poptimizer.shared import adapters, col, connections

# Где хранятся данные о дивидендах
DIV_COL = connections.MONGO_CLIENT["source"]["dividends"]


class WrongCurrencyError(config.POptimizerError):
    """Не верное наименование валюты в загруженных данных."""


class DividendsGateway(gateways.DivGateway):
    """Обновление данных из базы данных, заполняемой в ручную."""

    _logger = adapters.AsyncLogger()

    def __init__(
        self,
        div_col: collection.Collection = DIV_COL,
    ):
        """Сохраняет коллекцию для доступа к первоисточнику дивидендов."""
        super().__init__()
        self._collection = div_col

    async def __call__(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        self._logger(ticker)

        docs_cursor = self._collection.find(
            {"ticker": ticker},
            projection={"_id": False, "date": True, "dividends": True, "currency": True},
        )
        json = await docs_cursor.to_list(length=None)

        if not json:
            return pd.DataFrame(columns=[ticker, col.CURRENCY])

        df = pd.DataFrame.from_records(json, index="date")
        df.columns = [ticker, col.CURRENCY]

        cur_err = set(df[col.CURRENCY]) - {col.RUR, col.USD}
        if cur_err:
            raise WrongCurrencyError(cur_err)

        return df.sort_index(axis=0)
