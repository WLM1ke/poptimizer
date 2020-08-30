"""Загрузка данных по дивидендам."""
import pandas as pd
import pymongo

from poptimizer.data.adapters import db
from poptimizer.data.adapters.updaters import logger
from poptimizer.data.ports import base, names, outer

# Где хранятся данные о дивидендах
SOURCE_DB = "source"
SOURCE_COLLECTION = "dividends"


class DividendsUpdater(logger.LoggerMixin, outer.AbstractUpdater):
    """Обновление данных из базы данных, заполняемой в ручную."""

    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, base.DIVIDENDS)

        client = db.get_mongo_client()
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
        df.columns = [names.DATE, ticker]
        return df.set_index(names.DATE)
