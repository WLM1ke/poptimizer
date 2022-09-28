"""Сервис просмотра состава портфеля."""
from poptimizer.core import repository
from poptimizer.portfolio.edit import accounts
from poptimizer.portfolio.update import portfolio


class Service:
    """Сервис просмотра состава портфеля."""

    def __init__(self, repo: repository.Repo) -> None:
        self._repo = repo

    async def get_dates(self) -> accounts.AccountsDTO:
        """Возвращает перечень дат, на которые есть информация о портфеле + текущее значение."""
        dates = await self._repo.list(portfolio.Portfolio)

        return accounts.AccountsDTO(__root__=dates)

    async def get_portfolio(self, date: str) -> accounts.AccountDTO:
        """Выдает сводную информацию о портфеле по всем брокерским счетам на заданную дату.

        Для текущего портфеля оценка осуществляется по котировкам последнего торгового дня.
        """
        port = await self._repo.get(portfolio.Portfolio, date)

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
