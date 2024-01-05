from pydantic import PositiveInt

from poptimizer.core import domain
from poptimizer.data import securities


class Lots(domain.Response):
    lots: dict[str, PositiveInt]


class GetLots(domain.Request[Lots]):
    ...


class LotsRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetLots) -> Lots:  # noqa: ARG002
        table = await ctx.get(securities.Securities, for_update=False)

        return Lots(lots={sec.ticker: sec.lot for sec in table.df})
