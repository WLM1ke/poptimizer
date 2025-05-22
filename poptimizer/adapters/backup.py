import json
import logging
from typing import Any, Final

import aiofiles
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from poptimizer import consts, errors
from poptimizer.adapters import mongo
from poptimizer.domain.div import raw
from poptimizer.use_cases import handler

_DUMP: Final = consts.ROOT / "dump" / "dividends.json"


class BackupHandler:
    def __init__(self, mongo_repo: mongo.Repo) -> None:
        self._lgr = logging.getLogger()
        self._mongo_repo = mongo_repo

    async def __call__(self, ctx: handler.Ctx, msg: handler.AppStarted) -> None:  # noqa: ARG002
        try:
            all_docs = [div.model_dump(mode="json") async for div in self._mongo_repo.get_all(raw.DivRaw)]
        except PyMongoError as err:
            raise errors.AdapterError("can't check raw dividends") from err

        match len(all_docs):
            case 0:
                try:
                    await self.restore()
                except PyMongoError as err:
                    raise errors.AdapterError("can't restore raw dividends") from err
            case _:
                try:
                    await self._backup(all_docs)
                except PyMongoError as err:
                    raise errors.AdapterError("can't backup raw dividends") from err

    async def restore(self) -> None:
        if not _DUMP.exists():
            raise errors.AdapterError(f"can't restore raw dividends from {_DUMP}")

        async with aiofiles.open(_DUMP) as backup_file:  # type: ignore[reportUnknownMemberType]
            json_data = await backup_file.read()

        try:
            for doc in json.loads(json_data):
                div = raw.DivRaw.model_validate(doc)
                div_new = await self._mongo_repo.get(raw.DivRaw, div.uid)
                div_new.df = div.df
                await self._mongo_repo.save(div_new)
        except (PyMongoError, ValidationError) as err:
            raise errors.AdapterError("can't restore raw dividends") from err

        self._lgr.info("Raw dividends restored")

    async def _backup(self, all_docs: list[dict[str, Any]]) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(_DUMP, "w") as backup_file:  # type: ignore[reportUnknownMemberType]
            await backup_file.write(json.dumps(all_docs, indent=2, sort_keys=True))

        self._lgr.info("Raw dividends back up finished")
