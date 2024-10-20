import asyncio
from collections.abc import AsyncIterator

import async_lru
import numpy as np
import pandas as pd

from poptimizer.domain.data import trading_day
from poptimizer.domain.entity_ import entity, portfolio
from poptimizer.domain.entity_.data import quotes
from poptimizer.domain.entity_.data.div import div
from poptimizer.domain.service import domain_service


class Service:
    def __init__(self, repo: domain_service.Repo) -> None:
        self._repo = repo

    async def last_day(self) -> entity.Day:
        table = await self._repo.get(trading_day.TradingDay)

        return table.last

    async def portfolio_tickers(self) -> tuple[str, ...]:
        table = await self._repo.get(portfolio.Portfolio)

        return tuple(sorted(table.securities))

    async def _quote(
        self,
        last_day: pd.Timestamp,
        ticker: entity.Ticker,
    ) -> pd.DataFrame:
        table = await self._repo.get(quotes.Quotes, entity.UID(ticker))

        if not table.df:
            return pd.DataFrame(columns=["day", "open", "close", "high", "low", "turnover"], dtype="float64")

        doc = table.model_dump()["df"]

        return pd.DataFrame(doc).set_index("day").loc[:last_day]  # type: ignore[reportUnknownMemberType]

    @async_lru.alru_cache(maxsize=1)
    async def _quotes(
        self,
        last_day: pd.Timestamp,
        tickers: tuple[entity.Ticker, ...],
    ) -> list[pd.DataFrame]:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self._quote(last_day, ticker)) for ticker in tickers]

        return [task.result() for task in tasks]

    @async_lru.alru_cache(maxsize=1)
    async def close(
        self,
        last_day: pd.Timestamp,
        tickers: tuple[entity.Ticker, ...],
    ) -> pd.DataFrame:
        quotes_dfs = await self._quotes(last_day, tickers)
        close = pd.concat(  # type: ignore[reportUnknownMemberType]
            [quote["close"] for quote in quotes_dfs],  # type: ignore[PGH003]
            axis=1,
            sort=True,
        )
        close.columns = tickers

        return close.replace(to_replace=0, value=np.nan).ffill()  # type: ignore[reportUnknownMemberType]

    @async_lru.alru_cache(maxsize=1)
    async def turnover(
        self,
        last_day: pd.Timestamp,
        tickers: tuple[entity.Ticker, ...],
    ) -> pd.DataFrame:
        quotes_dfs = await self._quotes(last_day, tickers)
        turnover = pd.concat(  # type: ignore[reportUnknownMemberType]
            [quote["turnover"] for quote in quotes_dfs],  # type: ignore[PGH003]
            axis=1,
            sort=True,
        )
        turnover.columns = tickers

        return turnover.fillna(0)  # type: ignore[reportUnknownMemberType]

    async def dividends(self, ticker: str) -> AsyncIterator[tuple[pd.Timestamp, float]]:
        dividends = await self._repo.get(div.Dividends, entity.UID(ticker))

        for row in dividends.df:
            yield pd.Timestamp(row.day), row.dividend
