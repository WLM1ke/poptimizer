"""Конфигурация приложения."""
from types import MappingProxyType
from typing import Mapping, NamedTuple

from poptimizer.data import ports
from poptimizer.data.adapters import db
from poptimizer.data.adapters.updaters import conomy, dividends, dohod, smart_lab, trading_dates


class AppConfig(NamedTuple):
    """Описание конфигурации приложения."""

    db_session: ports.AbstractDBSession
    description_registry: ports.AbstractTableDescriptionRegistry


TRADING_DATES = ports.TableDescription(
    updater=trading_dates.TradingDatesUpdater(), index_checks=ports.IndexChecks.NO_CHECKS,
)
CONOMY = ports.TableDescription(updater=conomy.ConomyUpdater(), index_checks=ports.IndexChecks.ASCENDING)
DOHOD = ports.TableDescription(updater=dohod.DohodUpdater(), index_checks=ports.IndexChecks.ASCENDING)
SMART_LAB = ports.TableDescription(
    updater=smart_lab.SmartLabUpdater(), index_checks=ports.IndexChecks.NO_CHECKS,
)
DIVIDENDS = ports.TableDescription(
    updater=dividends.DividendsUpdater(), index_checks=ports.IndexChecks.UNIQUE_ASCENDING,
)

UPDATER_REGISTRY: Mapping[ports.GroupName, ports.TableDescription] = MappingProxyType(
    {
        ports.TRADING_DATES: TRADING_DATES,
        ports.CONOMY: CONOMY,
        ports.DOHOD: DOHOD,
        ports.SMART_LAB: SMART_LAB,
        ports.DIVIDENDS: DIVIDENDS,
    },
)
CONFIG = AppConfig(db_session=db.MongoDBSession(), description_registry=UPDATER_REGISTRY)


def get() -> AppConfig:
    """Возвращает конфигурацию приложения."""
    return CONFIG
