import json
import re
from typing import Final

import aiofiles
from pydantic import ValidationError

from poptimizer.core import actors, consts, errors
from poptimizer.domain.div import raw

_DUMP: Final = consts.ROOT / "dump" / "dividends.json"


class Client:
    async def migrate(self, ctx: actors.Ctx, last_version: str) -> bool:
        migrated = await _migrate(ctx, last_version)

        match divs := [div async for div in ctx.get_all(raw.DivRaw)]:
            case []:
                await _restore_dividends(ctx)
            case _:
                await _backup_dividends(ctx, divs)

        return migrated


async def _migrate(ctx: actors.Ctx, last_version: str) -> bool:  # noqa: ARG001
    if not last_version:
        return False

    migrated = False
    if _normalized_ver(last_version) < _normalized_ver("3.3.0"):
        ...

    return migrated


async def _restore_dividends(ctx: actors.Ctx) -> None:
    if not _DUMP.exists():
        raise errors.AdapterError(f"can't restore raw dividends from {_DUMP}")

    async with aiofiles.open(_DUMP) as backup_file:  # type: ignore[reportUnknownMemberType]
        json_data = await backup_file.read()

    try:
        for doc in json.loads(json_data):
            div = raw.DivRaw.model_validate(doc)
            div_new = await ctx.get_for_update(raw.DivRaw, div.uid)
            div_new.df = div.df
    except ValidationError as err:
        raise errors.AdapterError("can't restore raw dividends") from err

    ctx.info("raw dividends restored")


async def _backup_dividends(ctx: actors.Ctx, divs: list[raw.DivRaw]) -> None:
    _DUMP.parent.mkdir(parents=True, exist_ok=True)

    docs_with_divs = sorted(filter(lambda div: div.df, divs), key=lambda div: div.uid)

    async with aiofiles.open(_DUMP, "w") as backup_file:
        await backup_file.write(json.dumps(docs_with_divs, indent=2, sort_keys=True))

    ctx.info("raw dividends back up finished")


def _normalized_ver(ver: str) -> tuple[int, int, int]:
    result = re.match(r"(\d+)\.(\d+)\.(\d+)", ver)
    if not result:
        raise errors.AdapterError(f"Invalid version {ver}")

    return int(result.group(1)), int(result.group(2)), int(result.group(3))
