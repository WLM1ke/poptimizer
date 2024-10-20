from poptimizer.domain import consts, domain


class TradingDay(domain.Entity):
    last: domain.Day = consts.START_DAY

    def update_last_check(self, day: domain.Day) -> None:
        self.day = day

    def update_last_trading_day(self, day: domain.Day) -> None:
        self.day = day
        self.last = day
