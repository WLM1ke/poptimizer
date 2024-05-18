from poptimizer.domain import consts
from poptimizer.domain.entity import entity


class TradingDay(entity.Entity):
    last: entity.Day = consts.START_DAY

    def update_last_check(self, day: entity.Day) -> None:
        self.day = day

    def update_last_trading_day(self, day: entity.Day) -> None:
        self.day = day
        self.last = day
