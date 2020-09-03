"""Загрузка данных по дивидендам."""
import pandas as pd
import pymongo

from poptimizer.data.adapters.loaders import logger
from poptimizer.data.config import resources
from poptimizer.data.ports import base, col

# Где хранятся данные о дивидендах
SOURCE_DB = "source"
SOURCE_COLLECTION = "dividends"


class DividendsLoader(logger.LoggerMixin, base.AbstractLoader):
    """Обновление данных из базы данных, заполняемой в ручную."""

    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, base.DIVIDENDS)

        client = resources.get_mongo_client()
        collection = client[SOURCE_DB][SOURCE_COLLECTION]

        json = list(
            collection.aggregate(
                [
                    {"$match": {"ticker": ticker}},
                    {"$project": {"_id": False, "date": True, "dividends": True}},
                    {"$group": {"_id": "$date", ticker: {"$sum": "$dividends"}}},
                    {"$sort": {"_id": pymongo.ASCENDING}},
                ],
            ),
        )

        df = pd.DataFrame(json)
        df.columns = [col.DATE, ticker]
        return df.set_index(col.DATE)
