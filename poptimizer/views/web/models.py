from datetime import date
from enum import StrEnum, auto
from typing import Self

from aiohttp import web
from pydantic import BaseModel, Field

from poptimizer.domain import domain
from poptimizer.domain.domain import AccName, Ticker
from poptimizer.domain.portfolio import forecasts


class Theme(StrEnum):
    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


class Cookie(BaseModel):
    theme: Theme = Theme.SYSTEM
    hide_zero_positions: bool = False

    def toggle_zero_positions(self) -> None:
        self.hide_zero_positions = not self.hide_zero_positions

    @classmethod
    def from_request(cls, req: web.Request) -> Self:
        return cls.model_validate(req.cookies)


class Layout(BaseModel):
    selected_path: str
    poll: bool
    theme: Theme
    accounts: list[AccName]
    dividends: list[Ticker]


class Page(StrEnum):
    PORTFOLIO = auto()
    ACCOUNT = auto()
    FORECAST = auto()
    OPTIMIZATION = auto()
    DIVIDENDS = auto()
    SETTINGS = auto()


class BasePage(BaseModel):
    page: Page

    @property
    def title(self) -> str:
        return self.page.value.title()


class Row(BaseModel):
    label: str
    value: str


class Card(BaseModel):
    upper: str
    main: str
    row1: Row
    row2: Row
    row3: Row


class Position(BaseModel):
    ticker: domain.Ticker
    quantity: int
    lot: int
    price: float
    value: float


class Portfolio(BasePage):
    page: Page = Page.PORTFOLIO
    card: Card
    value: float
    cash: int
    positions: list[Position]


class Account(BasePage):
    page: Page = Page.ACCOUNT
    account: AccName
    card: Card
    value: float
    cash: int
    positions: list[Position]

    @property
    def title(self) -> str:
        return self.account


class Forecast(BasePage):
    page: Page = Page.FORECAST
    card: Card
    positions: list[forecasts.Position]


class Optimize(BasePage):
    page: Page = Page.OPTIMIZATION
    card: Card
    breakeven: float
    buy: list[forecasts.Position]
    sell: list[forecasts.Position]


class DivStatus(StrEnum):
    EXTRA = auto()
    OK = auto()
    MISSED = auto()


class DivRow(BaseModel):
    day: domain.Day
    dividend: float = Field(gt=0)
    status: DivStatus

    def to_tuple(self) -> tuple[date, float]:
        return self.day, self.dividend


class Dividends(BasePage):
    page: Page = Page.DIVIDENDS
    ticker: domain.UID
    dividends: list[DivRow]

    @property
    def title(self) -> str:
        return self.ticker

    @property
    def day(self) -> domain.Day:
        if len(self.dividends):
            return self.dividends[-1].day

        return date.today()

    @property
    def dividend(self) -> float:
        if len(self.dividends):
            return self.dividends[-1].dividend

        return 1


class Settings(BasePage):
    page: Page = Page.SETTINGS
    hide_accounts_zero_positions: bool = Field(default=False)
    accounts: list[AccName]
    exclude: list[domain.Ticker]
