from typing import Protocol

from poptimizer.actors.data.cpi import models
from poptimizer.core import actors


class CBRClient(Protocol):
    async def download_cpi(self) -> list[models.CPIRow]: ...


async def update(ctx: actors.CoreCtx, cbr_client: CBRClient) -> None:
    table = await ctx.get_for_update(models.CPI)

    row = await cbr_client.download_cpi()

    table.update(row)
