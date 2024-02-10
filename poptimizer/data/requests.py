import asyncio
from typing import Final

import pandas as pd

from poptimizer.core import domain
from poptimizer.data import quotes, reestry, securities, status
from poptimizer.data.contracts import (
    DivCompareRow,
    DivCompStatus,
    DividendsData,
    DivTickers,
    GetDividends,
    GetDivTickers,
    GetSecData,
    SecData,
    Security,
    UpdateDividends,
)

_START_LIQUIDITY_DAYS: Final = 21
_MINIMUM_HISTORY: Final = 86 * 5 + 21


class SecDataRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetSecData) -> SecData:
        sec_table = await ctx.get(securities.Securities, for_update=False)

        tickers = [sec.ticker for sec in sec_table.df]
        quotes = await _quotes(ctx, tickers)
        turnover = (  # type: ignore[reportUnknownMemberType]
            _turnover(tickers, quotes, pd.Timestamp(request.day))  # type: ignore[reportUnknownMemberType]
            .iloc[-_MINIMUM_HISTORY * 2 :]
            .sort_index(ascending=False)
            .expanding()
            .median()
            .iloc[_START_LIQUIDITY_DAYS:]
            .min()
        )

        return SecData(
            securities={
                sec.ticker: Security(
                    lot=sec.lot,
                    price=quotes[n].iloc[-1]["close"],  # type: ignore[reportUnknownMemberType]
                    turnover=turnover[sec.ticker],  # type: ignore[reportUnknownMemberType]
                )
                for n, sec in enumerate(sec_table.df)
                if not quotes[n].empty
            }
        )


def _turnover(
    tickers: list[str],
    quotes: list[pd.DataFrame],
    day: pd.Timestamp,
) -> pd.DataFrame:
    turnover = pd.concat(  # type: ignore[reportUnknownMemberType]
        [quote["turnover"] for quote in quotes],
        axis=1,
        sort=True,
    )
    turnover.columns = tickers

    return turnover.fillna(0).loc[:day]  # type: ignore[reportUnknownMemberType]


async def _quotes(ctx: domain.Ctx, tickers: list[domain.Ticker]) -> list[pd.DataFrame]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_quote(ctx, ticker)) for ticker in tickers]

    return [task.result() for task in tasks]


async def _quote(ctx: domain.Ctx, ticker: domain.Ticker) -> pd.DataFrame:
    table = await ctx.get(quotes.Quotes, domain.UID(ticker), for_update=False)

    if not table.df:
        return pd.DataFrame(columns=["day", "open", "close", "high", "low", "turnover"], dtype="float64")

    return pd.DataFrame(table.model_dump()["df"]).set_index("day")  # type: ignore[reportUnknownMemberType]


class DivTickersRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetDivTickers) -> DivTickers:  # noqa: ARG002
        table = await ctx.get(status.DivStatus, for_update=False)

        return DivTickers(tickers=[row.ticker for row in table.df])


class GetDividendsRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetDividends) -> DividendsData:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(status.DivRaw, domain.UID(request.ticker), for_update=False))
            reestry_task = tg.create_task(ctx.get(reestry.DivReestry, domain.UID(request.ticker), for_update=False))

        raw_table = raw_task.result()
        reestry_table = reestry_task.result()
        compare = [
            DivCompareRow(
                day=row_source.day,
                dividend=row_source.dividend,
                currency=row_source.currency,
                status=DivCompStatus.MISSED,
            )
            for row_source in reestry_table.df
            if not raw_table.has_row(row_source)
        ]

        for raw_row in raw_table.df:
            row_status = DivCompStatus.EXTRA
            if reestry_table.has_row(raw_row):
                row_status = DivCompStatus.OK

            compare.append(
                DivCompareRow(
                    day=raw_row.day,
                    dividend=raw_row.dividend,
                    currency=raw_row.currency,
                    status=row_status,
                ),
            )

        compare.sort(key=lambda compare: compare.to_tuple())

        return DividendsData(dividends=compare)


class UpdateDividendsRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: UpdateDividends) -> domain.Response:
        async with asyncio.TaskGroup() as tg:
            raw_task = tg.create_task(ctx.get(status.DivRaw, domain.UID(request.ticker)))
            quotes_task = tg.create_task(ctx.get(quotes.Quotes, domain.UID(request.ticker), for_update=False))

        raw_table = raw_task.result()
        quotes_table = quotes_task.result()
        first_day = quotes_table.df[0].day

        raw_table.update(
            quotes_table.day,
            [row for row in request.dividends if row.day >= first_day],
        )
        ctx.publish(status.RawDivUpdated(day=quotes_table.day))

        return domain.Response()
