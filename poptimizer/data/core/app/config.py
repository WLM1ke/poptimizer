"""Конфигурация приложения."""
from typing import NamedTuple

from poptimizer.data.core import ports
from poptimizer.data.infrastructure import db
from poptimizer.data.infrastructure.updaters import trading_dates


class AppConfig(NamedTuple):
    """Описание конфигурации приложения."""
    db_session: ports.AbstractDBSession
    updater: ports.AbstractUpdater


CONFIG = AppConfig(db_session=db.MongoDBSession(), updater=trading_dates.TradingDatesUpdater())


def get() -> AppConfig:
    """Возвращает конфигурацию приложения."""
    return CONFIG
