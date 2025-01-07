from poptimizer import consts
from poptimizer.domain import domain


class TradingDay(domain.Entity):
    portfolio_ver: domain.Version = domain.Version(0)
    last_check: domain.Day = consts.START_DAY

    def update_last_check(self, day: domain.Day) -> None:
        self.last_check = day

    def update_last_trading_day(self, day: domain.Day) -> None:
        self.day = day
        self.last_check = day
