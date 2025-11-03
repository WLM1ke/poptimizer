from poptimizer import consts
from poptimizer.domain import domain


class TradingDay(domain.Entity):
    last_check: domain.Day = consts.START_DAY
    poptimizer_ver: str = ""

    def update_last_check(self, day: domain.Day) -> None:
        self.last_check = day

    def update_last_trading_day(self, day: domain.Day, poptimizer_ver: str) -> None:
        self.day = day
        self.last_check = max(self.last_check, day)
        self.poptimizer_ver = poptimizer_ver
