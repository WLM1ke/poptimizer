"""Загрузка биржевых индексов."""
import asyncio
import logging
from datetime import datetime
from typing import Final

import aiohttp
import aiomoex
import pandas as pd

from poptimizer.data import domain
from poptimizer.data.repo import Repo

_INDEXES: Final = ("MCFTRR", "MEOGTRR", "IMOEX", "RVI")


class IndexesSrv:
    """Сервис загрузки биржевых индексов."""

    def __init__(self, repo: Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime) -> None:
        """Обновляет котировки биржевых индексов."""
        try:
            await asyncio.gather(*[self._update_one(update_day, index) for index in _INDEXES])
        except domain.DataError as err:
            self._logger.warning(f"can't complete Indexes update {err}")

            return

        self._logger.info("update is completed")

    async def _update_one(self, update_day: datetime, index: str) -> None:
        table = await self._repo.get(domain.Group.INDEXES, index)
        old_df = table.df

        start_date = None
        if old_df is not None:
            start_date = old_df.index[-1]

        try:
            new_df = await self._download(index, start_date, update_day)
        except aiomoex.client.ISSMoexError as err:
            raise domain.DataError(f"can't download {index}") from err

        if old_df is not None:
            new_df = pd.concat(
                [old_df.iloc[:-1], new_df],
                axis=0,
            )

        domain.raise_not_unique_increasing_index(new_df)
        domain.raise_dfs_mismatch(new_df, old_df)

        await self._repo.save(
            table.new_revision(
                df=new_df,
                timestamp=update_day,
            ),
        )

    async def _download(self, index: str, start_date: datetime | None, update_day: datetime) -> pd.DataFrame:
        start = None
        if start_date is not None:
            start = str(start_date.date())

        end = str(update_day.date)

        json = await aiomoex.get_market_history(
            session=self._session,
            start=start,
            end=end,
            security=index,
            columns=(
                "TRADEDATE",
                "OPEN",
                "CLOSE",
                "HIGH",
                "LOW",
                "VALUE",
            ),
            market="index",
        )

        new_df = pd.DataFrame(json)
        new_df.columns = [
            domain.Columns.DATE,
            domain.Columns.OPEN,
            domain.Columns.CLOSE,
            domain.Columns.HIGH,
            domain.Columns.LOW,
            domain.Columns.TURNOVER,
        ]
        new_df[domain.Columns.DATE] = pd.to_datetime(new_df[domain.Columns.DATE])

        return new_df.set_index(domain.Columns.DATE)
