"""Сервис для осуществления бэкапов и восстановлений."""
import logging
from pathlib import Path
from typing import ClassVar, Iterable, cast

import aiofiles
import bson
from motor.motor_asyncio import AsyncIOMotorClient

from poptimizer.core import consts, domain


class Service:
    """Сервис для осуществления бэкапов и восстановлений."""

    _dump: ClassVar = consts.ROOT_PATH / "dump"

    def __init__(self, mongo_client: AsyncIOMotorClient) -> None:
        self._logger = logging.getLogger("Backup")
        self._mongo = mongo_client

    async def backup(self, groups: Iterable[domain.Group]) -> None:
        """Делает резервную копию группы объектов."""
        for group in groups:
            await self._backup(group)
            self._logger.info(f"backup of {group} completed")

    async def restore(self, groups: Iterable[domain.Group]) -> None:
        """Восстанавливает резервную копию группы объектов при отсутствии данных в MongoDB."""
        for group in groups:
            if await self._mongo[group.module][group.group].count_documents({}):
                continue

            await self._restore(group)
            self._logger.info(f"initial {group} created")

    def _backup_path(self, group: domain.Group) -> Path:
        path = self._dump / group.module / f"{group.group}.bson"

        return cast(Path, path)

    async def _backup(self, group: domain.Group) -> None:
        path = self._backup_path(group)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "bw") as backup_file:
            async for batch in self._mongo[group.module][group.group].find_raw_batches():
                await backup_file.write(batch)

    async def _restore(self, group: domain.Group) -> None:
        path = self._backup_path(group)
        if not path.exists():
            self._logger.warning(f"backup file for {group} don't exists")

            return

        async with aiofiles.open(path, "br") as backup_file:
            raw = await backup_file.read()

        collection = self._mongo[group.module][group.group]

        await collection.insert_many(bson.decode_all(raw))
