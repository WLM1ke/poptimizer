"""Загрузка данных по дивидендам."""
import pandas as pd
import pymongo
from motor import motor_asyncio

from poptimizer.data_di.adapters import odm
from poptimizer.data_di.shared import adapters, col

# Где хранятся данные о дивидендах
SOURCE_DB = "source"
SOURCE_COLLECTION = "dividends"


class DividendsGateway:
    """Обновление данных из базы данных, заполняемой в ручную."""

    _logger = adapters.AsyncLogger()

    def __init__(
        self,
        mongo_client: motor_asyncio.AsyncIOMotorClient = odm.MONGO_CLIENT,
    ):
        """Сохраняет коллекцию для доступа к первоисточнику дивидендов."""
        self._collection = mongo_client[SOURCE_DB][SOURCE_COLLECTION]

    async def get(self, ticker: str) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        docs_cursor = self._collection.aggregate(
            [
                {"$match": {"ticker": ticker}},
                {"$project": {"date": True, "dividends": True}},
                {"$group": {"_id": "$date", ticker: {"$sum": "$dividends"}}},
                {"$sort": {"_id": pymongo.ASCENDING}},
            ],
        )
        json = await docs_cursor.to_list(length=None)
        df = pd.DataFrame(json, columns=["_id", ticker])

        df.columns = [col.DATE, ticker]
        return df.set_index(col.DATE)
