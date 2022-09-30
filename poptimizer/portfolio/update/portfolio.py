"""Сервис обновления стоимости и оборачиваемости портфеля."""
import bisect
import itertools
import logging
from datetime import datetime
from typing import Any, ClassVar, Final

import pandas as pd
from pydantic import BaseModel, Field, root_validator, validator

from poptimizer.core import consts, domain, repository
from poptimizer.data import adapter
from poptimizer.portfolio import exceptions

CURRENT_ID: Final = "Current"


class Position(BaseModel):
    """Позиция в портфеле."""

    ticker: str
    shares: dict[str, int]
    lot: int = Field(default=1, ge=1)
    price: float = Field(default=0, ge=0)
    turnover: float = Field(default=0, ge=0)

    @root_validator
    def _shares_positive_multiple_of_lots(cls, attr_dict: dict[str, Any]) -> dict[str, Any]:
        ticker = attr_dict["ticker"]
        lot = attr_dict["lot"]

        for acc, shares in attr_dict["shares"].items():
            if shares < 0:
                raise ValueError(f"{acc} {ticker} has negative shares")
            if shares % lot:
                raise ValueError(f"{acc} {ticker} is not multiple of lots {lot}")

        return attr_dict


class Portfolio(domain.BaseEntity):
    """Портфель."""

    group: ClassVar[domain.Group] = domain.Group.PORTFOLIO
    cash: dict[str, int] = Field(default_factory=dict)
    positions: list[Position] = Field(default_factory=list)

    def creat_account(self, name: str) -> None:
        """Добавляет счет в портфель."""
        if name in self.cash:
            raise exceptions.PortfolioEditError(f"can't add existing account {name}")

        self.cash[name] = 0

        for pos in self.positions:
            pos.shares[name] = 0

    def remove_account(self, name: str) -> None:
        """Удаляет пустой счет из портфеля."""
        if self.cash.pop(name):
            raise exceptions.PortfolioEditError(f"can't remove non empty account {name}")

        for pos in self.positions:
            if pos.shares.pop(name):
                raise exceptions.PortfolioEditError(f"can't remove non empty account {name}")

    def remove_ticker(self, ticker: str) -> None:
        """Удаляет существующий пустой тикер из портфеля."""
        count = bisect.bisect_left(self.positions, ticker, key=lambda position: position.ticker)
        if count == len(self.positions):
            raise exceptions.PortfolioEditError(f"no {ticker} in portfolio")
        if self.positions[count].ticker != ticker:
            raise exceptions.PortfolioEditError(f"no {ticker} in portfolio")

        for shares in self.positions.pop(count).shares.values():
            if shares:
                raise exceptions.PortfolioEditError(f"can't remove non empty ticker {ticker}")

    def add_ticker(self, ticker: str) -> None:
        """Добавляет отсутствующий тикер в портфель."""
        count = bisect.bisect_left(self.positions, ticker, key=lambda position: position.ticker)
        if count != len(self.positions):
            if self.positions[count].ticker == ticker:
                raise exceptions.PortfolioEditError(f"can't add existing {ticker} in portfolio")

        shares = {acc: 0 for acc in self.cash}

        self.positions.insert(
            count,
            Position(
                ticker=ticker,
                shares=shares,
            ),
        )

    @validator("cash")
    def _cash_must_be_positive(cls, cash: dict[str, int]) -> dict[str, int]:
        for acc, acc_cash in cash.items():
            if acc_cash < 0:
                raise ValueError(f"{acc} has negative cash")

        return cash

    @validator("positions")
    def _positions_must_sorted_by_ticker(cls, positions: list[Position]) -> list[Position]:
        ticker_pairs = itertools.pairwise(row.ticker for row in positions)

        if not all(ticker < next_ for ticker, next_ in ticker_pairs):
            raise ValueError("tickers are not sorted")

        return positions

    @root_validator
    def _same_accounts(cls, attr_dict: dict[str, Any]) -> dict[str, Any]:
        account = attr_dict["cash"].keys()

        for pos in attr_dict["positions"]:
            if (pos_acc := pos.shares.keys()) != account:
                raise ValueError(f"wrong {pos_acc} for {pos.ticker}")

        return attr_dict


class Service:
    """Сервис обновления стоимости и оборачиваемости портфеля."""

    def __init__(self, repo: repository.Repo, data_adapter: adapter.MarketData) -> None:
        self._logger = logging.getLogger("Portfolio")
        self._repo = repo
        self._adapter = data_adapter

    async def update(self, update_day: datetime) -> None:
        """Обновляет лоты и стоимость бумаг на счете."""
        await self._update(update_day)

        self._logger.info("update is completed")

    async def _update(self, update_day: datetime) -> None:
        port = await self._repo.get(Portfolio, CURRENT_ID)

        port = await self._update_lots(port)
        port = await self._update_market_data(port, update_day)

        await self._save_portfolio(port, update_day)

    async def _save_portfolio(self, port: Portfolio, update_day: datetime) -> None:
        if port.timestamp < update_day:
            port.timestamp = update_day

            port_old = port.copy()
            port_old.id_ = port.timestamp.date().isoformat()
            await self._repo.save(port_old)

        await self._repo.save(port)

    async def _update_lots(self, port: Portfolio) -> Portfolio:
        lots = (await self._adapter.securities())[adapter.Columns.LOT]

        for pos in port.positions:
            pos.lot = int(lots[pos.ticker])

        return port

    async def _update_market_data(self, port: Portfolio, update_day: datetime) -> Portfolio:
        tickers = tuple(pos.ticker for pos in port.positions)
        quotes = (await self._adapter.price(tickers)).loc[update_day]
        turnovers = await self._prepare_turnover(update_day, tickers)

        for pos in port.positions:
            ticker = pos.ticker
            pos.price = float(quotes[ticker])
            pos.turnover = float(turnovers[ticker])

        return port

    async def _prepare_turnover(self, timestamp: datetime, tickers: tuple[str, ...]) -> pd.Series:
        turnover = await self._adapter.turnover(tickers)
        turnover_last = turnover.loc[:timestamp].iloc[consts.LIQUIDITY_DAYS_UPPER :]  # type: ignore
        backward_expanding_median = turnover_last.sort_index(ascending=False).expanding().median()

        return backward_expanding_median.iloc[consts.LIQUIDITY_DAYS_LOWER :].min()
