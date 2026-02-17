from poptimizer.actors.data.cpi import models
from poptimizer.core import actors, adapters


async def update(ctx: actors.CoreCtx, cbr_client: adapters.CBRClient) -> None:
    table = await ctx.get_for_update(models.CPI)

    row = await cbr_client.download_cpi()

    table.update(row)
