"""Сервис редактирования выбранных тикеров."""
from pydantic import BaseModel

from poptimizer.core import repository
from poptimizer.data import adapter
from poptimizer.portfolio.exceptions import PortfolioEditError
from poptimizer.portfolio.update import portfolio


class Ticker(BaseModel):
    """Тикер с флагом выбран или нет."""

    ticker: str
    selected: bool


class DTO(BaseModel):
    """Перечень существующих тикеров с флагом выбраны или нет."""

    __root__: list[Ticker]


class Service:
    """Сервис редактирования перечня выбранных тикеров."""

    def __init__(self, repo: repository.Repo, adapter_data: adapter.MarketData) -> None:
        self._repo = repo
        self._adapter = adapter_data

    async def get(self) -> DTO:
        """Загружает информацию о выбранных тикерах."""
        dto, _ = await self._prepare_dto()

        return dto

    async def save(self, dto: DTO) -> None:
        """Сохраняет изменения выбранных тикеров."""
        dto_old, port = await self._prepare_dto()

        if len(dto_old.__root__) != len(dto.__root__):
            raise PortfolioEditError("wrong selected tickers dto length")

        for row, row_old in zip(dto.__root__, dto_old.__root__):
            if row.ticker != row_old.ticker:
                raise PortfolioEditError("wrong selected tickers dto sort order")

            match row.selected - row_old.selected:
                case 1:
                    port.add_ticker(row.ticker)
                case -1:
                    port.remove_ticker(row.ticker)

        await self._repo.save(port)

    async def _prepare_dto(self) -> tuple[DTO, portfolio.Portfolio]:
        port = await self._repo.get(portfolio.Portfolio, portfolio.CURRENT_ID)
        sec = {ticker: False for ticker in (await self._adapter.securities()).index}
        selected = {row.ticker: True for row in port.positions}

        rows = [
            Ticker(
                ticker=ticker,
                selected=selected,
            )
            for ticker, selected in (sec | selected).items()
        ]
        rows.sort(key=lambda row: row.ticker)

        return (
            DTO(
                __root__=rows,
            ),
            port,
        )
