from pathlib import Path
from typing import Final

import aiofiles
import bson

from poptimizer.core import errors
from poptimizer.io import mongo

_DUMP: Final = Path(__file__).parents[2] / "dump" / "dividends.bson"


class Backup:
    def __init__(self, collection: mongo.MongoCollection) -> None:
        self._collection = collection

    async def restore(self) -> None:
        if await self._collection.count_documents({}):
            return

        if not _DUMP.exists():
            raise errors.AdaptersError(f"can't restore {self._collection.name}")

        async with aiofiles.open(_DUMP, "br") as backup_file:
            raw = await backup_file.read()

        await self._collection.insert_many(bson.decode_all(raw))  # type: ignore[reportUnknownMemberType]

    async def backup(self) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(_DUMP, "bw") as backup_file:
            async for batch in self._collection.find_raw_batches():
                await backup_file.write(batch)
