import json
import re
from typing import Final, cast

import aiofiles
from pydantic import Field, ValidationError

from poptimizer.core import consts, domain, errors, fsm
from poptimizer.data.div import raw
from poptimizer.portfolio.models import portfolio
from poptimizer.portfolio.models.settings import Settings

_DUMP: Final = consts.ROOT / "dump" / "dividends.json"
_EXCLUDE_MOVED_IN: Final = "5.0.0"


class Portfolio(domain.Entity):
    """The pre-cut stored shape — read only, so the removed `exclude` can still be migrated."""

    exclude: set[domain.Ticker] = Field(default_factory=set[domain.Ticker])


class Client:
    async def migrate(self, ctx: fsm.Ctx, last_version: str) -> None:
        if _normalized_ver(last_version) < _normalized_ver(_EXCLUDE_MOVED_IN):
            await _move_exclude_to_settings(ctx)

    async def ensure_dividends(self, ctx: fsm.Ctx) -> None:
        match [div async for div in ctx.get_all(raw.DivRaw)]:
            case []:
                await _restore_dividends(ctx)
            case divs:
                await _backup_dividends(ctx, divs)


async def _move_exclude_to_settings(ctx: fsm.Ctx) -> None:
    old = await ctx.get(Portfolio)
    settings = await ctx.get_for_update(Settings)
    settings.exclude |= old.exclude

    await ctx.get_for_update(portfolio.Portfolio)


async def _restore_dividends(ctx: fsm.Ctx) -> None:
    if not _DUMP.exists():
        raise errors.AdapterError(f"can't restore raw dividends from {_DUMP}")

    async with aiofiles.open(_DUMP) as backup_file:
        json_data = await backup_file.read()

    try:
        for doc in cast("list[object]", json.loads(json_data)):
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
    result = re.prefixmatch(r"(\d+)\.(\d+)\.(\d+)", ver)
    if not result:
        raise errors.AdapterError(f"Invalid version {ver}")

    return int(result.group(1)), int(result.group(2)), int(result.group(3))
