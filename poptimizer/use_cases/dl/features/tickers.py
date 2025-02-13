import asyncio

from poptimizer.domain import domain
from poptimizer.domain.dl.features import EmbeddingFeatDesc, EmbFeat, Features
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler


class TickersFeatHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.IndexFeatUpdated) -> handler.TickersFeatUpdated:
        port = await ctx.get(portfolio.Portfolio)
        async with asyncio.TaskGroup() as tg:
            for n, pos in enumerate(port.positions):
                tg.create_task(_create_feat(ctx, n, pos.ticker, len(port.positions)))

        return handler.TickersFeatUpdated(day=msg.day)


async def _create_feat(ctx: handler.Ctx, pos_n: int, ticker: domain.Ticker, pos_count: int) -> None:
    feat = await ctx.get_for_update(Features, domain.UID(ticker))
    feat.embedding[EmbFeat.ticker] = EmbeddingFeatDesc(value=pos_n, size=pos_count)
