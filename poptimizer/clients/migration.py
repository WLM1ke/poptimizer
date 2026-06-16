import json
import re
from typing import Final

import aiofiles
from pydantic import ValidationError

from poptimizer.core import consts, errors, fsm
from poptimizer.data.div import raw

_DUMP: Final = consts.ROOT / "dump" / "dividends.json"


class Client:
    async def migrate(self, ctx: fsm.Ctx, last_version: str) -> None:  # noqa: ARG002
        if _normalized_ver(last_version) < _normalized_ver("3.3.0"):
            ...

    async def ensure_dividends(self, ctx: fsm.Ctx) -> None:
        match [div async for div in ctx.get_all(raw.DivRaw)]:
            case []:
                await _restore_dividends(ctx)
            case divs:
                await _backup_dividends(ctx, divs)


async def _restore_dividends(ctx: fsm.Ctx) -> None:
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

    ctx.info("Raw dividends restored")


async def _backup_dividends(ctx: fsm.Ctx, divs: list[raw.DivRaw]) -> None:
    _DUMP.parent.mkdir(parents=True, exist_ok=True)

    divs = sorted(filter(lambda div: div.df, divs), key=lambda div: div.uid)
    docs = [div.model_dump(mode="json") for div in divs]

    async with aiofiles.open(_DUMP, "w") as backup_file:
        await backup_file.write(json.dumps(docs, indent=2, sort_keys=True))

    ctx.info("Raw dividends back up finished")


def _normalized_ver(ver: str) -> tuple[int, int, int]:
    result = re.match(r"(\d+)\.(\d+)\.(\d+)", ver)
    if not result:
        raise errors.AdapterError(f"Invalid version {ver}")

    return int(result.group(1)), int(result.group(2)), int(result.group(3))
