import json
import logging
import re
from typing import Any, Final

import aiofiles
from pydantic import ValidationError

from poptimizer.core import actors, consts, domain, errors, message
from poptimizer.domain.div import raw
from poptimizer.domain.portfolio import forecasts

_DUMP: Final = consts.ROOT / "dump" / "dividends.json"


class MigrationState(actors.State):
    last_version: str = "0.0.0"


class MigrationActor:
    def __init__(self) -> None:
        self._lgr = logging.getLogger(self.__class__.__name__)

    async def __call__(self, ctx: actors.Ctx, state: MigrationState, msg: message.AppStarted) -> None:
        if state.last_version != msg.version:
            await self._migrate(ctx, state.last_version)
            state.last_version = msg.version

        match divs := [div async for div in ctx.get_all(raw.DivRaw)]:
            case []:
                await self.restore(ctx)
            case _:
                await self._backup(divs)

        ctx.send(message.MigrationFinished(), msg.next_aid)

    async def _migrate(self, ctx: actors.Ctx, last_version: str) -> None:
        # 2025-11-23
        if _normalized_ver(last_version) < _normalized_ver("3.3.0"):
            self._lgr.warning("dropping forecasts data due to new format")
            await ctx.drop(forecasts.Forecast)

    async def restore(self, ctx: actors.CoreCtx) -> None:
        if not _DUMP.exists():
            raise errors.ControllersError(f"can't restore raw dividends from {_DUMP}")

        async with aiofiles.open(_DUMP) as backup_file:  # type: ignore[reportUnknownMemberType]
            json_data = await backup_file.read()

        try:
            for doc in json.loads(json_data):
                div = raw.DivRaw.model_validate(doc)
                div_new = await ctx.get_for_update(raw.DivRaw, div.uid)
                div_new.df = div.df
        except ValidationError as err:
            raise errors.ControllersError("can't restore raw dividends") from err

        self._lgr.info("raw dividends restored")

    async def _backup(self, divs: list[raw.DivRaw]) -> None:
        _DUMP.parent.mkdir(parents=True, exist_ok=True)

        all_docs = [
            normalized for div in sorted(divs, key=lambda div: div.uid) if (normalized := _to_normalized_docs(div))
        ]

        async with aiofiles.open(_DUMP, "w") as backup_file:  # type: ignore[reportUnknownMemberType]
            await backup_file.write(json.dumps(all_docs, indent=2, sort_keys=True))

        self._lgr.info("raw dividends back up finished")


def _to_normalized_docs(div: raw.DivRaw) -> dict[str, Any] | None:
    if not div.df:
        return None

    div.rev = domain.Revision(uid=div.uid, ver=domain.Version(0))
    div.day = div.df[-1].day

    return div.model_dump(mode="json")


def _normalized_ver(ver: str) -> tuple[int, int, int]:
    result = re.match(r"(\d+)\.(\d+)\.(\d+)", ver)
    if not result:
        raise errors.ControllersError(f"Invalid version {ver}")

    return int(result.group(1)), int(result.group(2)), int(result.group(3))
