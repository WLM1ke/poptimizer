from pathlib import Path
from types import TracebackType
from typing import Final, Self

import aiofiles
import bson

from poptimizer.adapters import telegram
from poptimizer.core import errors
from poptimizer.io import mongo

_DUMP: Final = Path(__file__).parents[2] / "dump" / "dividends.bson"


class Backup:
    def __init__(self, lgr: telegram.Logger, collection: mongo.MongoCollection) -> None:
        self._lgr = lgr
        self._collection = collection

    async def __aenter__(self) -> Self:
        if await self._collection.count_documents({}):
            return self

        if not _DUMP.exists():
            raise errors.AdaptersError(f"can't restore {self._collection.name}")

        async with aiofiles.open(_DUMP, "br") as backup_file:
            raw = await backup_file.read()

        await self._collection.insert_many(bson.decode_all(raw))  # type: ignore[reportUnknownMemberType]
        self._lgr.info(f"Collection {self._collection.name} restored")

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(_DUMP, "bw") as backup_file:
            async for batch in self._collection.find_raw_batches():
                await backup_file.write(batch)

        self._lgr.info(f"Collection {self._collection.name} dumped")
