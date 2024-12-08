import bisect
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PlainSerializer,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from poptimizer import errors
from poptimizer.domain import domain

type AccountData = dict[domain.AccName, NonNegativeInt]


class Position(BaseModel):
    ticker: domain.Ticker
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat
    accounts: AccountData = Field(default_factory=dict)


class Portfolio(domain.Entity):
    account_names: Annotated[
        set[domain.AccName],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set)
    cash: AccountData = Field(default_factory=dict)
    positions: list[Position]

    @model_validator(mode="after")
    def _positions_have_know_accounts(self) -> Self:
        for position in self.positions:
            if unknown_accounts := position.accounts.keys() - self.account_names:
                raise ValueError(f"{position.ticker} has unknown accounts {unknown_accounts}")

        return self

    _must_be_sorted_by_ticker = field_validator("positions")(domain.sorted_with_ticker_field)

    @field_validator("positions")
    def _positions_are_multiple_of_lots(cls, positions: list[Position]) -> list[Position]:
        for position in positions:
            for acc, shares in position.accounts:
                ticker = position.ticker

                if shares % position.lot:
                    raise ValueError(f"{acc} has {shares} {ticker} - not multiple of lot of {position.lot} shares")

                if not shares:
                    raise ValueError(f"{acc} has zero {ticker} shares")

        return positions

    def tickers(self) -> tuple[domain.Ticker, ...]:
        return tuple(position.ticker for position in self.positions)

    def create_acount(self, name: domain.AccName) -> None:
        if name in self.account_names:
            raise errors.DomainError(f"account {name} already exists")

        if not name:
            raise errors.DomainError("account name is empty")

        self.account_names.add(name)

    def remove_acount(self, name: domain.AccName) -> None:
        if name not in self.account_names:
            raise errors.DomainError(f"account {name} doesn't exist")

        if name in self.cash:
            raise errors.DomainError(f"account {name} has not zero cash")

        for position in self.positions:
            if name in position.accounts:
                raise errors.DomainError(f"account {name} has not zero {position.ticker}")

    def find_position(self, ticker: domain.Ticker) -> tuple[int, Position | None]:
        n = bisect.bisect_left(self.positions, ticker, key=lambda pos: pos.ticker)
        if n == len(self.positions) or self.positions[n].ticker != ticker:
            return n, None

        return n, self.positions[n]

    def _try_remove_ticket(self, ticker: domain.Ticker) -> bool:
        match self.find_position(ticker):
            case (n, None):
                return False
            case (n, position):
                if position.accounts:
                    return False

                self.positions = self.positions[:n] + self.positions[n + 1 :]

                return True

    def update_position(self, acc_name: domain.AccName, ticker: domain.Ticker, amount: NonNegativeInt) -> None:
        if acc_name not in self.account_names:
            raise errors.DomainError(f"account {acc_name} doesn't exist")

        if ticker == domain.CashTicker:
            self.cash[acc_name] = amount

            return

        match self.find_position(ticker):
            case (_, None):
                raise errors.DomainError(f"ticker {ticker} doesn't exist")
            case (_, position):
                if amount % (lot := position.lot):
                    raise errors.DomainError(f"amount {amount} must be multiple of {lot}")

                if not amount:
                    position.accounts.pop(acc_name, None)

                position.accounts[acc_name] = amount
