import asyncio

import async_lru
import numpy as np
import pandas as pd

from poptimizer.domain.entity import entity, quotes
from poptimizer.domain.service import service


class Viewer:
    def __init__(self, repo: service.Repo) -> None:
        self._repo = repo

    async def _quote(
        self,
        last_day: pd.Timestamp,
        ticker: entity.Ticker,
    ) -> pd.DataFrame:
        table = await self._repo.get(quotes.Table, entity.UID(ticker))

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
            [quote["close"] for quote in quotes_dfs],
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
            [quote["turnover"] for quote in quotes_dfs],
            axis=1,
            sort=True,
        )
        turnover.columns = tickers

        return turnover.fillna(0)  # type: ignore[reportUnknownMemberType]
