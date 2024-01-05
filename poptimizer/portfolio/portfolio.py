from typing import Final, Self

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt, model_validator

from poptimizer.core import domain, errors
from poptimizer.data import contracts

_DEFAULT_ACCOUNT_NAME: Final = "Tinkoff"
_DEFAULT_ACCOUNT_CASH: Final = 200 * 1000**2


class Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat


class Account(BaseModel):
    cash: NonNegativeInt = 0
    positions: dict[str, PositiveInt] = Field(default_factory=dict)


class Portfolio(domain.Entity):
    accounts: dict[str, Account] = Field(
        default_factory=lambda: {_DEFAULT_ACCOUNT_NAME: Account(cash=_DEFAULT_ACCOUNT_CASH)}
    )
    securities: dict[str, Security] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _positions_are_multiple_of_lots(self) -> Self:
        for name, account in self.accounts.items():
            for ticker, shares in account.positions:
                if shares % (lot := self.securities[ticker].lot):
                    raise ValueError(f"{name} has {shares} {ticker} - not multiple of {lot} shares lot")

        return self

    @model_validator(mode="after")
    def _account_has_known_tickers(self) -> Self:
        for name, account in self.accounts.items():
            if unknown_tickers := account.positions.keys() - self.securities.keys():
                raise ValueError(f"{name} has {unknown_tickers}")

        return self

    def create_acount(self, name: str) -> None:
        if name in self.accounts:
            raise errors.DomainError(f"account {name} already exists")

        self.accounts[name] = Account()

    def remove_acount(self, name: str) -> None:
        if name not in self.accounts:
            raise errors.DomainError(f"account {name} doesn't exists")

        self.accounts.pop(name)


class PortfolioLotsUpdated(domain.Event):
    day: domain.Day


class PortfolioLotsHandler:
    async def handle(self, ctx: domain.Ctx, event: contracts.SecuritiesUpdated) -> None:
        port = await ctx.get(Portfolio)
        lots = await ctx.request(contracts.GetLots())

        for ticker, lot in lots.lots.items():
            if port_sec := port.securities.get(ticker):
                port_sec.lot = lot

        unknown_tickers = port.securities.keys() - lots.lots.keys()

        for ticker in unknown_tickers:
            can_be_removed = True
            for name, account in port.accounts.items():
                if ticker in account.positions:
                    ctx.publish_err(f"{name} has unknown ticker {ticker}")
                    can_be_removed = False

            if can_be_removed:
                port.securities.pop(ticker)

        ctx.publish(PortfolioLotsUpdated(day=event.day))
