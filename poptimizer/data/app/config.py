"""Конфигурация приложения."""
from types import MappingProxyType
from typing import Mapping, NamedTuple

from poptimizer.data import ports
from poptimizer.data.adapters import db
from poptimizer.data.adapters.updaters import conomy, dohod, smart_lab, trading_dates


class AppConfig(NamedTuple):
    """Описание конфигурации приложения."""

    db_session: ports.AbstractDBSession
    updaters_registry: ports.AbstractUpdatersRegistry


UPDATER_REGISTRY: Mapping[ports.GroupName, ports.AbstractUpdater] = MappingProxyType(
    {
        ports.TRADING_DATES: trading_dates.TradingDatesUpdater(),
        ports.CONOMY: conomy.ConomyUpdater(),
        ports.DOHOD: dohod.DohodUpdater(),
        ports.SMART_LAB: smart_lab.SmartLabUpdater(),
    },
)


CONFIG = AppConfig(db_session=db.MongoDBSession(), updaters_registry=UPDATER_REGISTRY)


def get() -> AppConfig:
    """Возвращает конфигурацию приложения."""
    return CONFIG
