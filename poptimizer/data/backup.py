"""Сервис для осуществления бэкапов и восстановлений."""
import logging
from pathlib import Path
from typing import ClassVar, Iterable, cast

import aiofiles
import bson
from motor.motor_asyncio import AsyncIOMotorDatabase

from poptimizer import config


class Service:
    """Сервис для осуществления бэкапов и восстановлений."""

    _dump: ClassVar = config.ROOT_PATH / "dump"

    def __init__(self, mongo_db: AsyncIOMotorDatabase) -> None:
        self._logger = logging.getLogger("Backup")
        self._mongo_db = mongo_db
        self._db_name = mongo_db.name

    async def backup(self, collections: Iterable[str]) -> None:
        """Делает резервную копию коллекций."""
        for col in collections:
            await self._backup(col)
            self._logger.info(f"backup of {self._db_name}.{col} completed")

    async def restore(self, collections: Iterable[str]) -> None:
        """Восстанавливает резервную копию коллекций при отсутствии данных в MongoDB."""
        for col in collections:
            if await self._mongo_db[col].count_documents({}):
                continue

            await self._restore(col)
            self._logger.info(f"initial {self._db_name}.{col} created")

    def _backup_name(self, collection: str) -> Path:
        return cast(Path, self._dump / self._db_name / f"{collection}.bson")

    async def _backup(self, collection: str) -> None:
        path = self._backup_name(collection)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "bw") as backup_file:
            async for batch in self._mongo_db[collection].find_raw_batches():
                await backup_file.write(batch)

    async def _restore(self, collection: str) -> None:
        path = self._backup_name(collection)
        if not path.exists():
            self._logger.warning(f"backup file for {self._db_name}.{collection} don't exists")

            return

        async with aiofiles.open(path, "br") as backup_file:
            raw = await backup_file.read()

        await self._mongo_db[collection].insert_many(bson.decode_all(raw))
