"""Адаптер для просмотра данных другими модулями."""
import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum, unique

import pandas as pd

from poptimizer.core import domain, repository


@unique
class Columns(str, Enum):  # noqa: WPS600
    """Существующие столбцы данных."""

    TICKER = "TICKER"
    LOT = "LOT"
    BOARD = "BOARD"
    TYPE = "TYPE"
    INSTRUMENT = "INSTRUMENT"

    DATE = "DATE"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    HIGH = "HIGH"
    LOW = "LOW"
    TURNOVER = "TURNOVER"

    def __str__(self) -> str:
        """Отображение в виде короткого текста."""
        return self.value


class MarketData:
    """Позволяет внешним модулям просматривать рыночную информацию в удобном виде."""

    def __init__(self, repo: repository.Repo) -> None:
        self._repo = repo

    async def securities(self) -> pd.DataFrame:
        """Информация о существующих ценных бумагах."""
        doc = await self._repo.get_doc(domain.Group.SECURITIES)

        df = (
            pd.DataFrame(doc["df"])
            .drop(columns="isin")
            .rename(
                columns={
                    "ticker": Columns.TICKER,
                    "lot": Columns.LOT,
                    "board": Columns.BOARD,
                    "type": Columns.TYPE,
                    "instrument": Columns.INSTRUMENT,
                },
            )
        )

        return df.set_index(Columns.TICKER)

    async def turnover(self, last_date: datetime, tickers: tuple[str, ...]) -> pd.DataFrame:
        """Информация об оборотах для заданных тикеров с заполненными пропусками."""
        dfs = await self._quotes(tickers)
        df = pd.concat(
            [df[Columns.TURNOVER] for df in dfs],
            axis=1,
            sort=True,
        )
        df.columns = tickers

        return df.fillna(0).loc[:last_date]  # type: ignore

    async def price(
        self,
        last_date: datetime,
        tickers: tuple[str, ...],
        price_type: Columns = Columns.CLOSE,
    ) -> pd.DataFrame:
        """Информация о ценах для заданных тикеров с заполненными пропусками."""
        dfs = await self._quotes(tickers)
        df = pd.concat(
            [df[price_type] for df in dfs],
            axis=1,
            sort=True,
        )
        df.columns = tickers

        return df.fillna(method="ffill").loc[:last_date]  # type: ignore

    async def dividends(self, ticker: str) -> AsyncIterator[tuple[datetime, float]]:
        """Дивиденды для заданного тикера."""
        doc = await self._repo.get_doc(domain.Group.DIVIDENDS, ticker)

        for row in doc["df"]:
            yield row["date"], row["dividend"]

    async def _quotes(self, tickers: tuple[str, ...]) -> list[pd.DataFrame]:
        aws = [self._repo.get_doc(domain.Group.QUOTES, ticker) for ticker in tickers]
        docs = await asyncio.gather(*aws)

        dfs = []

        for doc in docs:
            df = pd.DataFrame(doc["df"]).rename(
                columns={
                    "date": Columns.DATE,
                    "open": Columns.OPEN,
                    "close": Columns.CLOSE,
                    "high": Columns.HIGH,
                    "low": Columns.LOW,
                    "turnover": Columns.TURNOVER,
                },
            )

            dfs.append(df.set_index(Columns.DATE))

        return dfs
