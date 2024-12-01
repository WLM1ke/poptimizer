from typing import Final, Self

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt, model_validator

from poptimizer import errors
from poptimizer.domain import domain

_CashTicker: Final = domain.Ticker("CASH")


class Account(BaseModel):
    cash: NonNegativeInt = 0
    positions: dict[domain.Ticker, PositiveInt] = Field(default_factory=dict)


class PortfolioWeights(BaseModel):
    day: domain.Day
    version: int
    cash: NonNegativeFloat = Field(repr=False)
    positions: dict[domain.Ticker, NonNegativeFloat] = Field(repr=False)


class Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat


class Portfolio(domain.Entity):
    accounts: dict[domain.AccName, Account] = Field(default_factory=dict)
    securities: dict[domain.Ticker, Security] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _positions_are_multiple_of_lots(self) -> Self:
        for name, account in self.accounts.items():
            for ticker, shares in account.positions.items():
                if shares % (lot := self.securities[ticker].lot):
                    raise ValueError(f"{name} has {shares} {ticker} - not multiple of {lot} shares lot")

        return self

    @model_validator(mode="after")
    def _account_has_known_tickers(self) -> Self:
        for name, account in self.accounts.items():
            if unknown_tickers := account.positions.keys() - self.securities.keys():
                raise ValueError(f"{name} has {unknown_tickers}")

        return self

    @property
    def value(self) -> float:
        value = 0
        for account in self.accounts.values():
            value += account.cash

            for ticker, shares in account.positions.items():
                value += shares * self.securities[ticker].price

        return value

    def create_acount(self, name: domain.AccName) -> None:
        if name in self.accounts:
            raise errors.DomainError(f"account {name} already exists")

        if not name:
            raise errors.DomainError("account name is empty")

        self.accounts[name] = Account()

    def remove_acount(self, name: domain.AccName) -> None:
        account = self.accounts.pop(name, None)
        if account is None:
            raise errors.DomainError(f"account {name} doesn't exist")

        if account.cash or account.positions:
            self.accounts[name] = account

            raise errors.DomainError(f"account {name} is not empty")

    def remove_ticket(self, ticker: domain.Ticker) -> bool:
        for account in self.accounts.values():
            if ticker in account.positions:
                return False

        self.securities.pop(ticker)

        return True

    def update_position(self, name: domain.AccName, ticker: domain.Ticker, amount: NonNegativeInt) -> None:
        if (account := self.accounts.get(name)) is None:
            raise errors.DomainError(f"account {name} doesn't exist")

        if ticker != _CashTicker and ticker not in self.securities:
            raise errors.DomainError(f"ticker {ticker} doesn't exist")

        if ticker == _CashTicker:
            account.cash = amount

            return

        if amount % (lot := self.securities[ticker].lot):
            raise errors.DomainError(f"amount {amount} must be multiple of {lot}")

        if not amount:
            account.positions.pop(ticker, None)

            return

        account.positions[ticker] = amount

    def get_non_zero_weights(self) -> PortfolioWeights:
        port_value = 0
        cash = 0
        pos_value = {ticker: 0.0 for ticker in self.securities}

        for account in self.accounts.values():
            port_value += account.cash
            cash += account.cash

            for ticker, amount in account.positions.items():
                value = self.securities[ticker].price * amount
                port_value += value
                pos_value[ticker] += value

        if port_value == 0:
            return PortfolioWeights(
                day=self.day,
                version=self.ver,
                cash=1,
                positions=pos_value,
            )

        return PortfolioWeights(
            day=self.day,
            version=self.ver,
            cash=cash / port_value,
            positions={ticker: pos / port_value for ticker, pos in pos_value.items()},
        )
