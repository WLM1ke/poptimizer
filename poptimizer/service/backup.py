from pathlib import Path
from typing import Final

import aiofiles
import bson

from poptimizer.adapter import mongo
from poptimizer.service import logging, service

_DUMP: Final = Path(__file__).parents[2] / "dump" / "dividends.bson"


class Service:
    def __init__(
        self,
        logging_service: logging.Service,
        collection: mongo.MongoCollection,
    ) -> None:
        self._logging_service = logging_service
        self._collection = collection

    async def restore(self) -> None:
        if await self._collection.count_documents({}):
            return

        if not _DUMP.exists():
            raise service.ServiceError(f"can't restore {self._collection.name}")

        async with aiofiles.open(_DUMP, "br") as backup_file:
            raw = await backup_file.read()

        await self._collection.insert_many(bson.decode_all(raw))  # type: ignore[reportUnknownMemberType]
        self._logging_service.info(f"Collection {self._collection.name} restored")

    async def backup(self) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(_DUMP, "bw") as backup_file:
            async for batch in self._collection.find_raw_batches():
                await backup_file.write(batch)

        self._logging_service.info(f"Collection {self._collection.name} dumped")
