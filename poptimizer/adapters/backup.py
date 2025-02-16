import logging
from typing import Final

import aiofiles
import bson
import pymongo
from pymongo.errors import PyMongoError

from poptimizer import consts, errors
from poptimizer.adapters import adapter, mongo
from poptimizer.domain.div import raw
from poptimizer.use_cases import handler

_DUMP: Final = consts.ROOT / "dump" / "dividends.bson"


class BackupHandler:
    def __init__(self, mongo_db: mongo.MongoDatabase) -> None:
        self._lgr = logging.getLogger()
        self._collection = mongo_db[adapter.get_component_name(raw.DivRaw)]

    async def __call__(self, ctx: handler.Ctx, msg: handler.AppStarted) -> None:  # noqa: ARG002
        try:
            count = await self._collection.count_documents({})
        except PyMongoError as err:
            raise errors.AdapterError("can't check raw dividends collection") from err

        match count:
            case 0:
                try:
                    await self._restore()
                except PyMongoError as err:
                    raise errors.AdapterError("can't restore raw dividends collection") from err
            case _:
                try:
                    await self._backup()
                except PyMongoError as err:
                    raise errors.AdapterError("can't backup raw dividends collection") from err

    async def _restore(self) -> None:
        if not _DUMP.exists():
            raise errors.AdapterError(f"can't restore dividends collection from {_DUMP}")

        async with aiofiles.open(_DUMP, "br") as backup_file:
            raw = await backup_file.read()

        await self._collection.insert_many(bson.decode_all(raw))  # type: ignore[reportUnknownMemberType]
        self._lgr.info("Collection %s restored", self._collection.name)

    async def _backup(self) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(_DUMP, "bw") as backup_file:
            async for batch in self._collection.find_raw_batches(sort={"_id": pymongo.ASCENDING}):  # type: ignore[reportUnknownMemberType]
                await backup_file.write(batch)  # type: ignore[reportUnknownMemberType]

        self._lgr.info("Collection %s dumped", self._collection.name)
