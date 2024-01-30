from pathlib import Path
from typing import Final

import aiofiles
import bson

from poptimizer.core import domain
from poptimizer.data import day_started, status
from poptimizer.io import mongo

_DUMP: Final = Path(__file__).parents[2] / "dump" / "dividends.bson"


class DividendsBackupCompleted(domain.Event):
    day: domain.Day


class DividendsRestoreCompleted(domain.Event):
    day: domain.Day


class DivBackupEventHandler:
    def __init__(self, collection: mongo.MongoCollection) -> None:
        self._collection = collection

    async def handle(self, ctx: domain.Ctx, event: status.RawDivUpdated | day_started.DayStarted) -> None:
        match event:
            case status.RawDivUpdated():
                await self._backup(ctx, event)
            case day_started.DayStarted():
                await self._restore(ctx, event)

    async def _backup(self, ctx: domain.Ctx, event: status.RawDivUpdated) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(_DUMP, "bw") as backup_file:
            async for batch in self._collection.find_raw_batches():
                await backup_file.write(batch)

        ctx.publish(DividendsBackupCompleted(day=event.day))

    async def _restore(self, ctx: domain.Ctx, event: day_started.DayStarted) -> None:
        if await self._collection.count_documents({}):
            return

        if not _DUMP.exists():
            ctx.warn("can't restore dividends - no backup")

            return

        async with aiofiles.open(_DUMP, "br") as backup_file:
            raw = await backup_file.read()

        await self._collection.insert_many(bson.decode_all(raw))  # type: ignore[reportUnknownMemberType]

        ctx.publish(DividendsRestoreCompleted(day=event.day))
