"""Сервис редактирования выбранных тикеров."""
import logging

from pydantic import BaseModel

from poptimizer.data.exceptions import EditError
from poptimizer.data.repo import Repo
from poptimizer.data.update import securities


class Ticker(BaseModel):
    """Тикер с флагом выбран или нет."""

    ticker: str
    selected: bool


class DTO(BaseModel):
    """Перечень существующих тикеров с флагом выбраны или нет."""

    tickers: list[Ticker]


class Service:
    """Сервис редактирования перечня выбранных тикеров."""

    def __init__(self, repo: Repo) -> None:
        self._logger = logging.getLogger("SecEdit")
        self._repo = repo

    async def get(self) -> DTO:
        """Загружает информацию о выбранных тикерах."""
        table = await self._repo.get(securities.Table)

        return DTO(
            tickers=[
                Ticker(
                    ticker=row.ticker,
                    selected=row.selected,
                )
                for row in table.df
            ],
        )

    async def save(self, dto: DTO) -> None:
        """Сохраняет изменения выбранных тикеров."""
        table = await self._repo.get(securities.Table)

        if len(table.df) != len(dto.tickers):
            raise EditError("wrong selected tickers dto length")

        for count, row in enumerate(dto.tickers):
            if table.df[count].ticker != row.ticker:
                raise EditError("wrong selected tickers dto sort order")

            table.df[count].selected = row.selected

        await self._repo.save(table)
