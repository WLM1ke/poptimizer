import asyncio

from poptimizer.core import domain, fsm
from poptimizer.data.features.features import EmbeddingSeqFeatDesc, EmbSeqFeat, Features
from poptimizer.portfolio.port import portfolio


async def update(ctx: fsm.Ctx, trading_days: list[domain.Day]) -> None:
    async with asyncio.TaskGroup() as tg:
        port = await ctx.get(portfolio.Portfolio)

        for pos in port.positions:
            tg.create_task(_create_day_feats(ctx, domain.UID(pos.ticker), trading_days))


async def _create_day_feats(ctx: fsm.Ctx, ticker: domain.UID, trading_days: domain.TradingDays) -> None:
    feat = await ctx.get_for_update(Features, ticker)

    feat.embedding_seq[EmbSeqFeat.WEEK_DAY] = EmbeddingSeqFeatDesc(
        sequence=[trading_days[-n].timetuple().tm_wday for n in reversed(range(1, len(feat.numerical) + 1))],
        size=7,
    )
    feat.embedding_seq[EmbSeqFeat.WEEK] = EmbeddingSeqFeatDesc(
        sequence=[trading_days[-n].isocalendar().week - 1 for n in reversed(range(1, len(feat.numerical) + 1))],
        size=53,
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
