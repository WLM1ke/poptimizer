"""События связанные с таблицами."""
import dataclasses
import datetime

from poptimizer.data_di.shared import domain


@dataclasses.dataclass(frozen=True)
class AppStarted(domain.AbstractEvent):
    """Начало работы приложения.

    Обработчики данного события должны осуществить всю необходимую инициализацию.
    """

    timestamp: datetime.datetime = dataclasses.field(
        init=False,
        default_factory=datetime.datetime.utcnow,
    )


@dataclasses.dataclass(frozen=True)
class TradingDayEnded(domain.AbstractEvent):
    """Произошло окончание очередного торгового дня."""

    date: datetime.date


@dataclasses.dataclass(frozen=True)
class TradingDayEndedTQBR(domain.AbstractEvent):
    """Произошло окончание очередного торгового дня в режиме TQBR."""

    date: datetime.date


@dataclasses.dataclass(frozen=True)
class TickerTraded(domain.AbstractEvent):
    """Тикер торговался в указанный день."""

    ticker: str
    date: datetime.date
