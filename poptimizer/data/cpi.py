"""Загрузка данных о потребительской инфляции."""
import logging
import types
from datetime import datetime
from typing import Final

import aiohttp
import aiomoex
import pandas as pd

from poptimizer.data import domain
from poptimizer.data.repo import Repo

HEADERS: Final = types.MappingProxyType({"User-Agent": "POptimizer"})

_URL: Final = "https://rosstat.gov.ru/storage/mediabank/ipc_4(2).xlsx"
END_OF_JAN: Final = 31
PARSING_PARAMETERS: Final = types.MappingProxyType(
    {
        "sheet_name": "01",
        "header": 3,
        "skiprows": [4],
        "skipfooter": 3,
        "index_col": 0,
        "engine": "openpyxl",
    },
)
NUM_OF_MONTH: Final = 12
FIRST_YEAR: Final = 1991
FIRST_MONTH: Final = "январь"


class CPISrv:
    """Сервис загрузки потребительской инфляции."""

    def __init__(self, repo: Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime) -> None:
        """Обновляет потребительскую инфляцию и логирует неудачную попытку."""
        try:
            await self._update(update_day)
        except domain.DataError as err:
            self._logger.warning(f"can't complete CPI update {err}")

            return

        self._logger.info("update is completed")

    async def _update(self, update_day: datetime) -> None:
        try:
            raw_df = await self._download()
        except aiomoex.client.ISSMoexError as err:
            raise domain.DataError("can't download CPI") from err

        _validate_raw_df(raw_df)

        df = _transform_raw_df(raw_df)

        await self._validate_new_df(df)

        await self._repo.save(
            domain.Table(
                group=domain.Group.CPI,
                df=df,
                timestamp=update_day,
            ),
        )

    async def _download(self) -> pd.DataFrame:
        async with self._session.get(_URL, headers=HEADERS) as resp:
            if not resp.ok:
                raise domain.DataError(f"bad CPI respond status {resp.reason}")

            xlsx_file = await resp.read()

        return pd.read_excel(
            xlsx_file,
            **PARSING_PARAMETERS,
        )

    async def _validate_new_df(self, new_df: pd.DataFrame) -> None:
        domain.raise_not_unique_increasing_index(new_df)

        table = await self._repo.get(domain.Group.CPI)
        domain.raise_dfs_mismatch(new_df, table.df)


def _validate_raw_df(df: pd.DataFrame) -> None:
    months, _ = df.shape
    if months != NUM_OF_MONTH:
        raise domain.DataError(f"table have {months} must be 12")

    first_year = df.columns[0]
    if first_year != FIRST_YEAR:
        raise domain.DataError(f"first year {first_year} must be 1991")

    first_month = df.index[0]
    if first_month != FIRST_MONTH:
        raise domain.DataError(f"fist mount {first_month} must be {FIRST_MONTH}")


def _transform_raw_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.transpose().stack()
    first_year = df.index[0][0]
    df.index = pd.date_range(
        name=domain.Columns.DATE,
        freq="M",
        start=pd.Timestamp(year=first_year, month=1, day=END_OF_JAN),
        periods=len(df),
    )
    df = df.div(100)

    return df.to_frame(domain.Columns.VALUE)
