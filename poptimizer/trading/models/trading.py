import uuid

from pydantic import BaseModel

from poptimizer.core import consts, domain
from poptimizer.portfolio.models import portfolio


class Instrument(BaseModel):
    uuid: uuid.UUID
    ticker: domain.Ticker
    isin: str


class TradingState(domain.Entity):
    day: domain.Day = consts.START_DAY

    def init_day(self, port: portfolio.Portfolio) -> None:
        self.day = port.day
