from typing import Final, NewType, Self

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt, model_validator

from poptimizer.core import domain, errors
from poptimizer.data import contracts

AccName = NewType("AccName", str)
Ticker = NewType("Ticker", str)

_CashTicker: Final = Ticker("CASH")


class Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat


class Account(BaseModel):
    cash: NonNegativeInt = 0
    positions: dict[Ticker, PositiveInt] = Field(default_factory=dict)


class Portfolio(domain.Entity):
    accounts: dict[AccName, Account] = Field(default_factory=dict)
    securities: dict[Ticker, Security] = Field(default_factory=dict)

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

    def create_acount(self, name: AccName) -> None:
        if name in self.accounts:
            raise errors.DomainError(f"account {name} already exists")

        if not name:
            raise errors.DomainError("account name is empty")

        self.accounts[name] = Account()

    def remove_acount(self, name: AccName) -> None:
        account = self.accounts.pop(name, None)
        if account is None:
            raise errors.DomainError(f"account {name} doesn't exist")

        if account.cash or account.positions:
            self.accounts[name] = account

            raise errors.DomainError(f"account {name} is not empty")

    def remove_ticket(self, ticker: Ticker) -> bool:
        for account in self.accounts.values():
            if ticker in account.positions:
                return False

        self.securities.pop(ticker)

        return True

    def update_position(self, name: AccName, ticker: Ticker, amount: NonNegativeInt) -> None:
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


class PortfolioDataUpdated(domain.Event):
    day: domain.Day


class PortfolioEventHandler:
    async def handle(self, ctx: domain.Ctx, event: contracts.QuotesUpdated) -> None:
        port = await ctx.get(Portfolio)
        sec_data = await ctx.request(contracts.GetSecData(day=event.day))

        _remove_not_traded(ctx, port, sec_data)
        _update_sec_data(ctx, port, sec_data)
        _add_liquid(ctx, port, sec_data)
        port.timestamp = event.day

        ctx.publish(PortfolioDataUpdated(day=event.day))


def _remove_not_traded(ctx: domain.Ctx, port: Portfolio, sec_data: contracts.SecData) -> None:
    not_traded = port.securities.keys() - sec_data.securities.keys()

    for ticker in not_traded:
        port.securities[ticker].turnover = 0

        match port.remove_ticket(ticker):
            case True:
                ctx.warn(f"not traded {ticker} is removed")
            case False:
                ctx.warn(f"not traded {ticker} is not removed")


def _update_sec_data(ctx: domain.Ctx, port: Portfolio, sec_data: contracts.SecData) -> None:
    min_turnover = port.value / (max(1, len(port.securities)))
    traded = port.securities.keys() & sec_data.securities.keys()

    for ticker in traded:
        cur_data = port.securities[ticker]
        new_data = sec_data.securities[ticker]

        cur_data.lot = new_data.lot
        cur_data.price = new_data.price
        cur_data.turnover = new_data.turnover

        if cur_data.turnover > min_turnover:
            continue

        match port.remove_ticket(ticker):
            case True:
                ctx.warn(f"not liquid {ticker} is removed")
            case False:
                ctx.warn(f"not liquid {ticker} is not removed")


def _add_liquid(ctx: domain.Ctx, port: Portfolio, sec_data: contracts.SecData) -> None:
    min_turnover = port.value / (max(1, len(port.securities)))
    not_port = sec_data.securities.keys() - port.securities.keys()

    for ticker in not_port:
        new_data = sec_data.securities[ticker]

        if new_data.turnover > min_turnover:
            port.securities[Ticker(ticker)] = Security(
                lot=new_data.lot,
                price=new_data.price,
                turnover=new_data.turnover,
            )

            ctx.warn(f"{ticker} is added")
