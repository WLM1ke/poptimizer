import logging
from pathlib import Path
from typing import Final

import aiofiles
import bson

from poptimizer import errors
from poptimizer.adapters import adapter, mongo
from poptimizer.domain.div import raw
from poptimizer.use_cases import handler

_DUMP: Final = Path(__file__).parents[3] / "dump" / "dividends.bson"


class BackupHandler:
    def __init__(self, mongo_db: mongo.MongoDatabase) -> None:
        self._lgr = logging.getLogger()
        self._collection = mongo_db[adapter.get_component_name(raw.DivRaw)]

    async def __call__(self, ctx: handler.Ctx, msg: handler.AppStarted) -> None:  # noqa: ARG002
        match await self._collection.count_documents({}):
            case 0:
                await self._restore()
            case _:
                await self._backup()

    async def _restore(self) -> None:
        if await self._collection.count_documents({}):
            return

        if not _DUMP.exists():
            raise errors.ControllersError(f"can't restore {self._collection.name} from {_DUMP}")

        async with aiofiles.open(_DUMP, "br") as backup_file:
            raw = await backup_file.read()

        await self._collection.insert_many(bson.decode_all(raw))  # type: ignore[reportUnknownMemberType]
        self._lgr.info("Collection %s restored", self._collection.name)

    async def _backup(self) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(_DUMP, "bw") as backup_file:
            async for batch in self._collection.find_raw_batches():  # type: ignore[reportUnknownMemberType]
                await backup_file.write(batch)  # type: ignore[reportUnknownMemberType]

        self._lgr.info("Collection %s dumped", self._collection.name)
