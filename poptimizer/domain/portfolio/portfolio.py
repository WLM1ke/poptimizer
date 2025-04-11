import bisect
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
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

from poptimizer import consts, errors
from poptimizer.domain import domain

type AccountData = dict[domain.AccName, NonNegativeInt]


class Position(BaseModel):
    ticker: domain.Ticker
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat
    accounts: AccountData = Field(default_factory=dict)


class NormalizedPosition(BaseModel):
    ticker: domain.Ticker
    weight: float = Field(ge=0, le=1)
    norm_turnover: NonNegativeFloat


class Portfolio(domain.Entity):
    trading_interval: float = Field(consts.INITIAL_FORECAST_DAYS, ge=1)
    sold: NonNegativeInt = 0
    account_names: Annotated[
        set[domain.AccName],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set)
    cash: AccountData = Field(default_factory=dict)
    positions: Annotated[
        list[Position],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list)
    exclude: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set)

    @model_validator(mode="after")
    def _positions_have_know_accounts(self) -> Self:
        for position in self.positions:
            if unknown_accounts := position.accounts.keys() - self.account_names:
                raise ValueError(f"{position.ticker} has unknown accounts {unknown_accounts}")

        return self

    @field_validator("positions")
    def _positions_are_multiple_of_lots(cls, positions: list[Position]) -> list[Position]:
        for position in positions:
            for acc, shares in position.accounts.items():
                ticker = position.ticker

                if shares % position.lot:
                    raise ValueError(f"{acc} has {shares} {ticker} - not multiple of lot of {position.lot} shares")

                if not shares:
                    raise ValueError(f"{acc} has zero {ticker} shares")

        return positions

    @property
    def forecast_days(self) -> int:
        return int(self.trading_interval)

    def update_forecast_days(self, trading_days: list[domain.Day]) -> None:
        old_day = self.day
        self.day = trading_days[-1]

        if not self.ver:
            old_day = self.day

        pos_count = sum(1 for pos in self.positions if pos.accounts if pos.accounts)
        if not pos_count:
            self.sold = 0

            return

        for day in reversed(trading_days):
            if day <= old_day:
                break

            self.trading_interval = self.trading_interval + 1 / int(self.trading_interval)
            if self.sold:
                self.trading_interval -= self.sold / pos_count
                self.trading_interval = max(1, self.trading_interval)
                self.sold = 0

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

        self.account_names.remove(name)

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

            if not amount:
                self.cash.pop(acc_name)

            return

        match self.find_position(ticker):
            case (_, None):
                raise errors.DomainError(f"ticker {ticker} doesn't exist")
            case (_, position):
                if amount % (lot := position.lot):
                    raise errors.DomainError(f"amount {amount} must be multiple of {lot}")

                position.accounts[acc_name] = amount

                if not amount:
                    position.accounts.pop(acc_name)

                if not position.accounts:
                    self.sold += 1

    def normalized_turnover(self) -> list[float]:
        values = [position.price * sum(position.accounts.values()) for position in self.positions]
        port_value = sum(values) + sum(self.cash.values())

        return [position.turnover / port_value for position in self.positions]

    @property
    def normalized_positions(self) -> list[NormalizedPosition]:
        values = [pos.price * sum(pos.accounts.values()) for pos in self.positions]
        port_value = sum(values) + sum(self.cash.values())
        if not port_value:
            port_value = 1

        return [
            NormalizedPosition(
                ticker=pos.ticker,
                weight=value / port_value,
                norm_turnover=pos.turnover / port_value,
            )
            for pos, value in zip(self.positions, values, strict=True)
        ]

    @property
    def value(self) -> float:
        values = [pos.price * sum(pos.accounts.values()) for pos in self.positions]

        return sum(values) + sum(self.cash.values())

    def exclude_ticker(self, ticker: domain.Ticker) -> None:
        _, pos = self.find_position(ticker)
        if pos is None:
            raise errors.DomainError(f"ticker {ticker} is not in portfolio")

        self.exclude.add(ticker)

    def not_exclude_ticker(self, ticker: domain.Ticker) -> None:
        if ticker not in self.exclude:
            raise errors.DomainError(f"ticker {ticker} is not excluded")

        self.exclude.remove(ticker)
