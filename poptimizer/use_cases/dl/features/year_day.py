import asyncio

from poptimizer.domain import domain
from poptimizer.domain.dl.features import EmbeddingSeqFeatDesc, EmbSeqFeat, Features
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler


class YearDayFeatHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.IndexFeatUpdated) -> handler.YearDayFeatUpdated:
        async with asyncio.TaskGroup() as tg:
            port = await ctx.get(portfolio.Portfolio)

            for pos in port.positions:
                tg.create_task(_create_year_day_feat(ctx, domain.UID(pos.ticker), msg.trading_days))

        return handler.YearDayFeatUpdated(day=msg.day)


async def _create_year_day_feat(ctx: handler.Ctx, ticker: domain.UID, trading_days: domain.TradingDays) -> None:
    feat = await ctx.get_for_update(Features, ticker)

    feat.embedding_seq[EmbSeqFeat.YEAR_DAY] = EmbeddingSeqFeatDesc(
        sequence=[trading_days[-n].timetuple().tm_yday for n in reversed(range(1, len(feat.numerical) + 1))],
        size=366,
    )
