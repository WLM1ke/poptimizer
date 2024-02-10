from datetime import date
from typing import NewType

from pydantic import BaseModel, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt

from poptimizer.core import domain


class PortfolioDataUpdated(domain.Event):
    day: domain.Day
    version: int
    cash_weight: NonNegativeFloat = Field(repr=False)
    positions_weight: dict[domain.Ticker, NonNegativeFloat] = Field(repr=False)


AccName = NewType("AccName", str)


class Account(BaseModel):
    cash: NonNegativeInt = 0
    positions: dict[domain.Ticker, PositiveInt] = Field(default_factory=dict)


class Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat


class PortfolioData(domain.Response):
    day: date
    accounts: dict[AccName, Account]
    securities: dict[domain.Ticker, Security]


class GetPortfolio(domain.Request[PortfolioData]):
    ...


class CreateAccount(domain.Request[PortfolioData]):
    name: str


class RemoveAccount(domain.Request[PortfolioData]):
    name: str


class UpdatePosition(domain.Request[PortfolioData]):
    name: str
    ticker: str
    amount: NonNegativeInt
