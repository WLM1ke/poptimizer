from typing import Protocol

from poptimizer.domain import domain


class Bus(Protocol):
    def publish(self, msg: domain.Msg) -> None: ...


class TradingDayCheckRequired(domain.Msg): ...


class DataUpdateFinished(domain.Msg): ...
