from poptimizer.core import consts, domain
from poptimizer.portfolio.models import portfolio


class TradingState(domain.Entity):
    day: domain.Day = consts.START_DAY

    def init_day(self, port: portfolio.Portfolio) -> None:
        self.day = port.day
