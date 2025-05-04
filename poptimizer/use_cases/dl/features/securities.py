import asyncio

from poptimizer.domain import domain
from poptimizer.domain.dl.features import EmbeddingFeatDesc, EmbFeat, Features
from poptimizer.domain.moex import securities
from poptimizer.domain.portfolio import portfolio
from poptimizer.use_cases import handler


class SecFeatHandler:
    async def __call__(self, ctx: handler.Ctx, msg: handler.DayFeatUpdated) -> handler.SecFeatUpdated:
        async with asyncio.TaskGroup() as tg:
            sec_task = tg.create_task(ctx.get(securities.Securities))
            port = await ctx.get(portfolio.Portfolio)
            feat = [tg.create_task(ctx.get_for_update(Features, domain.UID(pos.ticker))) for pos in port.positions]

            sec_types, types_count = _prepare_sec_types(port, await sec_task)
            pos_count = len(port.positions)

            for n, feat_task in enumerate(feat):
                feat = await feat_task
                feat.embedding[EmbFeat.TICKER] = EmbeddingFeatDesc(value=n, size=pos_count)
                feat.embedding[EmbFeat.TICKER_TYPE] = EmbeddingFeatDesc(value=sec_types[feat.uid], size=types_count)

        return handler.SecFeatUpdated(day=msg.day)


def _sec_type(row: securities.Row) -> str:
    return f"{row.board}.{row.type}.{row.instrument}"


def _prepare_sec_types(
    port: portfolio.Portfolio,
    sec: securities.Securities,
) -> tuple[dict[domain.UID, int], int]:
    types_cache = {row.ticker: _sec_type(row) for row in sec.df}

    types_str = {domain.UID(pos.ticker): types_cache.get(pos.ticker, "") for pos in port.positions}
    types_number = {sec_type: n for n, sec_type in enumerate(sorted(set(types_str.values())))}

    return (
        {ticker: types_number[type_str] for ticker, type_str in types_str.items()},
        len(types_number),
    )
