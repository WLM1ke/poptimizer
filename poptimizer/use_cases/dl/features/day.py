import asyncio

from poptimizer.domain import domain
from poptimizer.domain.dl.features import EmbeddingSeqFeatDesc, EmbSeqFeat, Features
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler


class DayFeatHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.IndexFeatUpdated) -> handler.DayFeatUpdated:
        async with asyncio.TaskGroup() as tg:
            port = await ctx.get(portfolio.Portfolio)

            for pos in port.positions:
                tg.create_task(_create_day_feats(ctx, domain.UID(pos.ticker), msg.trading_days))

        return handler.DayFeatUpdated(day=msg.day)


async def _create_day_feats(ctx: handler.Ctx, ticker: domain.UID, trading_days: domain.TradingDays) -> None:
    feat = await ctx.get_for_update(Features, ticker)

    feat.embedding_seq[EmbSeqFeat.WEEK_DAY] = EmbeddingSeqFeatDesc(
        sequence=[trading_days[-n].timetuple().tm_wday for n in reversed(range(1, len(feat.numerical) + 1))],
        size=7,
    )
    feat.embedding_seq[EmbSeqFeat.MONTH_DAY] = EmbeddingSeqFeatDesc(
        sequence=[trading_days[-n].timetuple().tm_mday - 1 for n in reversed(range(1, len(feat.numerical) + 1))],
        size=31,
    )
    feat.embedding_seq[EmbSeqFeat.MONTH] = EmbeddingSeqFeatDesc(
        sequence=[trading_days[-n].timetuple().tm_mon - 1 for n in reversed(range(1, len(feat.numerical) + 1))],
        size=12,
    )
    feat.embedding_seq[EmbSeqFeat.YEAR_DAY] = EmbeddingSeqFeatDesc(
        sequence=[trading_days[-n].timetuple().tm_yday for n in reversed(range(1, len(feat.numerical) + 1))],
        size=366,
    )
