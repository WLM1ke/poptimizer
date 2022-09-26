"""Сервис просмотра состава портфеля."""
from datetime import datetime

from poptimizer.core import repository
from poptimizer.portfolio.edit import accounts
from poptimizer.portfolio.update import portfolio


class Service:
    """Сервис просмотра состава портфеля."""

    def __init__(self, repo: repository.Repo) -> None:
        self._repo = repo

    async def get_dates(self) -> accounts.AccountsDTO:
        """Возвращает перечень дат, на которые есть информация о портфеле."""
        dates = await self._repo.list_timestamps(portfolio.Portfolio)

        return accounts.AccountsDTO(__root__=[date.date().isoformat() for date in dates])

    async def get_portfolio(self, date: str) -> accounts.AccountDTO:
        """Выдает сводную информацию о портфеле по всем брокерским счетам."""
        port = await self._repo.get_by_timestamp(portfolio.Portfolio, datetime.strptime(date, "%Y-%m-%d"))

        cash = sum(port.cash.values())
        positions = [
            accounts.PositionDTO(
                ticker=pos.ticker,
                shares=sum(pos.shares.values()),
                lot=pos.lot,
                price=pos.price,
                turnover=pos.turnover,
            )
            for pos in port.positions
        ]

        return accounts.AccountDTO(
            cash=cash,
            positions=positions,
        )
