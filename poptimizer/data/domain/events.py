"""События связанные с таблицами."""
import dataclasses
import datetime
from typing import Optional

import pandas as pd

from poptimizer.shared import domain


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
class USDUpdated(domain.AbstractEvent):
    """Произошло обновление курса."""

    date: datetime.date
    usd: pd.DataFrame = dataclasses.field(repr=False)


@dataclasses.dataclass(frozen=True)
class TickerTraded(domain.AbstractEvent):
    """Тикер торговался в указанный день."""

    ticker: str
    isin: str
    market: str
    date: datetime.date
    usd: pd.DataFrame = dataclasses.field(repr=False)


@dataclasses.dataclass(frozen=True)
class IndexCalculated(domain.AbstractEvent):
    """Биржа пересчитала значение индекса в связи с окончанием торгового дня."""

    ticker: str
    date: datetime.date


@dataclasses.dataclass(frozen=True)
class DivExpected(domain.AbstractEvent):
    """Ожидаются дивиденды для тикера."""

    ticker: str
    df: pd.DataFrame = dataclasses.field(repr=False)


@dataclasses.dataclass(frozen=True)
class UpdateDivCommand(domain.AbstractEvent):
    """Команда обновить дивиденды."""

    ticker: str
    usd: Optional[pd.DataFrame] = dataclasses.field(default=None, repr=False)
