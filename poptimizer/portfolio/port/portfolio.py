import bisect
from datetime import UTC, datetime, timedelta
from typing import Annotated, Final, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
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

from poptimizer.core import consts, domain, errors

_UPDATE_INTERVAL: Final = timedelta(minutes=30)

type AccountData = dict[domain.AccName, NonNegativeInt]


class Position(BaseModel):
    ticker: domain.Ticker
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat
    accounts: AccountData = Field(default_factory=dict[domain.AccName, int])

    def quantity(self, account: domain.AccName | None = None) -> int:
        if account is None:
            return sum(self.accounts.values())

        return self.accounts.get(account, 0)

    def value(self, account: domain.AccName | None = None) -> float:
        return self.price * self.quantity(account)


class NormalizedPosition(BaseModel):
    ticker: domain.Ticker
    weight: float = Field(ge=0, le=1)
    norm_turnover: NonNegativeFloat
    accounts: list[domain.AccName]


class Portfolio(domain.Entity):
    day: domain.Day = consts.START_DAY
    updated_at: Annotated[
        AwareDatetime,
        PlainSerializer(lambda dt: int(dt.timestamp()), return_type=int),
    ] = Field(default_factory=lambda: datetime.now(UTC) - _UPDATE_INTERVAL)
    holding_period: NonNegativeFloat = 0
    new_positions: NonNegativeInt = 0
    account_names: Annotated[
        set[domain.AccName],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.AccName])
    cash: AccountData = Field(default_factory=dict[domain.AccName, int])
    positions: Annotated[
        list[Position],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list[Position])
    exclude: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.Ticker])
    illiquid: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.Ticker])

    def need_update(self) -> bool:
        return datetime.now(UTC) - self.updated_at > _UPDATE_INTERVAL

    def update_finished(self) -> None:
        self.updated_at = datetime.now(UTC)

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
        return int(max(1, self.holding_period))

    @property
    def tickers(self) -> domain.Tickers:
        return tuple(pos.ticker for pos in self.positions)

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

    def update_position(self, acc_name: domain.AccName, ticker: domain.Ticker, quantity: NonNegativeInt) -> None:
        if acc_name not in self.account_names:
            raise errors.DomainError(f"account {acc_name} doesn't exist")

        if ticker == domain.CashTicker:
            self.cash[acc_name] = quantity

            if not quantity:
                self.cash.pop(acc_name)

            return

        match self.find_position(ticker):
            case (_, None):
                raise errors.DomainError(f"{ticker} not in portfolio")
            case (_, position):
                if quantity % (lot := position.lot):
                    raise errors.DomainError(f"quantity {quantity} must be multiple of {lot}")

                if not position.accounts and quantity:
                    self.new_positions += 1

                position.accounts[acc_name] = quantity

                if not quantity:
                    position.accounts.pop(acc_name)

    def normalized_turnover(self) -> list[float]:
        values = self.value()

        return [position.turnover / values for position in self.positions]

    @property
    def normalized_positions(self) -> list[NormalizedPosition]:
        port_value = self.value()

        if not port_value:
            port_value = 1

        return [
            NormalizedPosition(
                ticker=pos.ticker,
                weight=pos.value() / port_value,
                norm_turnover=pos.turnover / port_value,
                accounts=sorted(pos.accounts),
            )
            for pos in self.positions
        ]

    def cash_value(self, account: domain.AccName | None = None) -> int:
        if account is None:
            return sum(self.cash.values())

        return self.cash.get(account, 0)

    def value(self, account: domain.AccName | None = None) -> float:
        if account is None:
            return sum(pos.price * sum(pos.accounts.values()) for pos in self.positions) + self.cash_value()

        return sum(pos.price * pos.accounts.get(account, 0) for pos in self.positions) + self.cash_value(account)

    def open_positions(self, account: domain.AccName | None = None) -> int:
        if account is None:
            return sum(bool(pos.accounts) for pos in self.positions)

        return sum(account in pos.accounts for pos in self.positions)

    @property
    def effective_positions(self) -> float:
        positions_value = sum(pos.value() for pos in self.positions)

        if not positions_value:
            return 0

        return positions_value**2 / sum(pos.value() ** 2 for pos in self.positions)

    def exclude_ticker(self, ticker: domain.Ticker) -> None:
        _, pos = self.find_position(ticker)
        if pos is None:
            raise errors.DomainError(f"ticker {ticker} is not in portfolio")

        self.exclude.add(ticker)
        self.illiquid.add(ticker)

    def not_exclude_ticker(self, ticker: domain.Ticker) -> None:
        if ticker not in self.exclude:
            raise errors.DomainError(f"ticker {ticker} is not excluded")

        self.exclude.remove(ticker)
