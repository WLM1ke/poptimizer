"""Сервис редактирования брокерских счетов."""
from pydantic import BaseModel

from poptimizer.core import repository
from poptimizer.portfolio.exceptions import PortfolioEditError
from poptimizer.portfolio.update import portfolio


class AccountsDTO(BaseModel):
    """Перечень существующих брокерских счетов."""

    __root__: list[str]


class PositionDTO(BaseModel):
    """Позиция по тикеру на конкретном счете."""

    ticker: str
    shares: int
    lot: int
    price: float
    turnover: float


class AccountDTO(BaseModel):
    """Информация о составе отдельного брокерского счета с рыночными данными."""

    cash: int
    positions: list[PositionDTO]


class SharesDTO(BaseModel):
    """Информация об измененном количестве бумаг на брокерском счете."""

    ticker: str
    shares: int


class AccountUpdateDTO(BaseModel):
    """Информация о составе отдельного брокерского счета без рыночных данных."""

    cash: int
    positions: list[SharesDTO]


class Service:
    """Сервис редактирования перечня выбранных тикеров."""

    def __init__(self, repo: repository.Repo) -> None:
        self._repo = repo

    async def get_account_names(self) -> AccountsDTO:
        """Возвращает перечень существующих брокерских счетов."""
        port = await self._repo.get(portfolio.Portfolio, portfolio.CURRENT_ID)

        return AccountsDTO(__root__=list(port.cash))

    async def create_account(self, acc_name: str) -> None:
        """Создает брокерский счет, если он не существует."""
        port = await self._repo.get(portfolio.Portfolio, portfolio.CURRENT_ID)

        port.creat_account(acc_name)

        await self._repo.save(port)

    async def remove_account(self, acc_name: str) -> None:
        """Удаляет брокерский счет, если он пустой."""
        port = await self._repo.get(portfolio.Portfolio, portfolio.CURRENT_ID)

        port.remove_account(acc_name)

        await self._repo.save(port)

    async def get_account(self, acc_name: str) -> AccountDTO:
        """Информация о составе брокерского счета."""
        port = await self._repo.get(portfolio.Portfolio, portfolio.CURRENT_ID)

        if (cash := port.cash.pop(acc_name, None)) is None:
            raise PortfolioEditError(f"account {acc_name} don't exist")

        positions = [
            PositionDTO(
                ticker=pos.ticker,
                shares=pos.shares[acc_name],
                lot=pos.lot,
                price=pos.price,
                turnover=pos.turnover,
            )
            for pos in port.positions
        ]

        return AccountDTO(
            cash=cash,
            positions=positions,
        )

    async def update_account(self, acc_name: str, update: AccountUpdateDTO) -> None:
        """Обновляет данные о количестве бумаг на счете."""
        port = await self._repo.get(portfolio.Portfolio, portfolio.CURRENT_ID)
        if acc_name not in port.cash:
            raise PortfolioEditError(f"account {acc_name} don't exist")

        port.cash[acc_name] = update.cash

        if len(port.positions) != (count := len(update.positions)):
            raise PortfolioEditError(f"wrong positions count {count}")

        update.positions.sort(key=lambda pos: pos.ticker)

        for pos_port, pos_update in zip(port.positions, update.positions):
            if pos_port.ticker != pos_update.ticker:
                raise PortfolioEditError(f"wrong positions order {pos_update.ticker}")

            pos_port.shares[acc_name] = pos_update.shares

        await self._repo.save(port)
