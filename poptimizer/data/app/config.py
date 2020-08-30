"""Конфигурация приложения."""
from types import MappingProxyType
from typing import Mapping, NamedTuple

from poptimizer.data.adapters import db
from poptimizer.data.adapters.updaters import (
    conomy,
    cpi,
    dividends,
    dohod,
    moex,
    smart_lab,
    trading_dates,
)
from poptimizer.data.ports import app, base, outer


class AppConfig(NamedTuple):
    """Описание конфигурации приложения."""

    db_session: outer.AbstractDBSession
    description_registry: app.AbstractTableDescriptionRegistry


TRADING_DATES = app.TableDescription(
    updater=trading_dates.TradingDatesUpdater(),
    index_checks=app.IndexChecks.NO_CHECKS,
    validate=False,
)
CONOMY = app.TableDescription(
    updater=conomy.ConomyUpdater(),
    index_checks=app.IndexChecks.ASCENDING,
    validate=False,
)
DOHOD = app.TableDescription(
    updater=dohod.DohodUpdater(),
    index_checks=app.IndexChecks.ASCENDING,
    validate=False,
)
SMART_LAB = app.TableDescription(
    updater=smart_lab.SmartLabUpdater(),
    index_checks=app.IndexChecks.NO_CHECKS,
    validate=False,
)
DIVIDENDS = app.TableDescription(
    updater=dividends.DividendsUpdater(),
    index_checks=app.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
CPI = app.TableDescription(
    updater=cpi.CPIUpdater(),
    index_checks=app.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)
SECURITIES = app.TableDescription(
    updater=moex.SecuritiesUpdater(),
    index_checks=app.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
INDEX = app.TableDescription(
    updater=moex.IndexUpdater(),
    index_checks=app.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)

UPDATER_REGISTRY: Mapping[base.GroupName, app.TableDescription] = MappingProxyType(
    {
        base.TRADING_DATES: TRADING_DATES,
        base.CONOMY: CONOMY,
        base.DOHOD: DOHOD,
        base.SMART_LAB: SMART_LAB,
        base.DIVIDENDS: DIVIDENDS,
        base.CPI: CPI,
        base.SECURITIES: SECURITIES,
        base.INDEX: INDEX,
    },
)
CONFIG = AppConfig(db_session=db.MongoDBSession(), description_registry=UPDATER_REGISTRY)


def get() -> AppConfig:
    """Возвращает конфигурацию приложения."""
    return CONFIG
