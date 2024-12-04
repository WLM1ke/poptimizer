from poptimizer.domain import domain


class Forecast(domain.Entity):
    def init_day(
        self,
        day: domain.Day,
    ) -> None:
        self.day = day
