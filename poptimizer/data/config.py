"""Конфигурация приложения."""
import datetime
from types import MappingProxyType
from typing import Final, Mapping

from poptimizer.data.adapters import db
from poptimizer.data.adapters.loaders import (
    conomy,
    cpi,
    dividends,
    dohod,
    moex,
    smart_lab,
    trading_dates,
)
from poptimizer.data.app import services
from poptimizer.data.ports import app, base, outer

TRADING_DATES = outer.TableDescription(
    loader=trading_dates.TradingDatesLoader(),
    index_checks=base.IndexChecks.NO_CHECKS,
    validate=False,
)
CONOMY = outer.TableDescription(
    loader=conomy.ConomyLoader(),
    index_checks=base.IndexChecks.ASCENDING,
    validate=False,
)
DOHOD = outer.TableDescription(
    loader=dohod.DohodLoader(),
    index_checks=base.IndexChecks.ASCENDING,
    validate=False,
)
SMART_LAB = outer.TableDescription(
    loader=smart_lab.SmartLabLoader(),
    index_checks=base.IndexChecks.NO_CHECKS,
    validate=False,
)
DIVIDENDS = outer.TableDescription(
    loader=dividends.DividendsLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
CPI = outer.TableDescription(
    loader=cpi.CPILoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)
SECURITIES = outer.TableDescription(
    loader=moex.SecuritiesLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
INDEX = outer.TableDescription(
    loader=moex.IndexLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)

TABLES_REGISTRY: Mapping[base.GroupName, outer.TableDescription] = MappingProxyType(
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
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)
DB_SESSION = db.MongoDBSession()
CONFIG = app.Config(
    event_bus=services.EventsBus(TABLES_REGISTRY, DB_SESSION),
    viewer=services.Viewer(TABLES_REGISTRY, DB_SESSION),
    start_date=START_DATE,
)


def get() -> app.Config:
    """Возвращает конфигурацию приложения."""
    return CONFIG
