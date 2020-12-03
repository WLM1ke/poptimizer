"""Загрузка данных по дивидендам."""
import pandas as pd
import pymongo

from poptimizer.data.adapters import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import outer
from poptimizer.shared import col

# Где хранятся данные о дивидендах
SOURCE_DB = "source"
SOURCE_COLLECTION = "dividends"


class DividendsLoader(logger.LoaderLoggerMixin, outer.AbstractLoader):
    """Обновление данных из базы данных, заполняемой в ручную."""

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, outer.DIVIDENDS)

        collection = resources.get_mongo_client()[SOURCE_DB][SOURCE_COLLECTION]

        docs_cursor = collection.aggregate(
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
