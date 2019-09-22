"""Менеджер данных для дивидендов."""
from typing import Optional, Any, List, Dict

import pymongo

from poptimizer.store import manager
from poptimizer.store.manager import AbstractManager
from poptimizer.store.mongo import SOURCE_DB, COLLECTION, DB
from poptimizer.store.utils import DATE


class Dividends(AbstractManager):
    """Дивиденды и время закрытия реестра для акций.

    Данные создаются с нуля, так как могут быть ретроспективные исправления ошибок.
    """

    CREATE_FROM_SCRATCH = True

    def __init__(self, db=DB) -> None:
        super().__init__(collection=COLLECTION, db=db, create_from_scratch=True)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает полностью данные по дивидендам.

        Загрузка осуществляется из обновляемой в ручную MongoDB базы данных по дивидендам."""
        source = self._mongo.client[SOURCE_DB][COLLECTION]
        data = list(
            source.aggregate(
                [
                    {"$match": {"ticker": item}},
                    {"$project": {"_id": False, "date": True, "dividends": True}},
                    {"$group": {"_id": "$date", item: {"$sum": "$dividends"}}},
                    {"$sort": {"_id": pymongo.ASCENDING}},
                ]
            )
        )
        formatter = dict(_id=lambda x: (DATE, x))
        return manager.data_formatter(data, formatter)
