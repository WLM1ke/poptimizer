"""Конфигурация приложения."""
import datetime
from types import MappingProxyType
from typing import Final

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
from poptimizer.data.domain import repo
from poptimizer.data.ports import base, outer

_TRADING_DATES = base.TableDescription(
    loader=trading_dates.TradingDatesLoader(),
    index_checks=base.IndexChecks.NO_CHECKS,
    validate=False,
)
_CONOMY = base.TableDescription(
    loader=conomy.ConomyLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_DOHOD = base.TableDescription(
    loader=dohod.DohodLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_SMART_LAB = base.TableDescription(
    loader=smart_lab.SmartLabLoader(),
    index_checks=base.IndexChecks.NO_CHECKS,
    validate=False,
)
_DIVIDENDS = base.TableDescription(
    loader=dividends.DividendsLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_CPI = base.TableDescription(
    loader=cpi.CPILoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)
_SECURITIES = base.TableDescription(
    loader=moex.SecuritiesLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_INDEX = base.TableDescription(
    loader=moex.IndexLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)
_QUOTES = base.TableDescription(
    loader=moex.QuotesLoader(),
    index_checks=base.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)

_TABLES_REGISTRY: outer.TableDescriptionRegistry = MappingProxyType(
    {
        base.TRADING_DATES: _TRADING_DATES,
        base.CONOMY: _CONOMY,
        base.DOHOD: _DOHOD,
        base.SMART_LAB: _SMART_LAB,
        base.DIVIDENDS: _DIVIDENDS,
        base.CPI: _CPI,
        base.SECURITIES: _SECURITIES,
        base.INDEX: _INDEX,
        base.QUOTES: _QUOTES,
    },
)
_DB_SESSION = db.MongoDBSession()


def repo_factory() -> repo.Repo:
    """Создает репо."""
    return repo.Repo(_TABLES_REGISTRY, _DB_SESSION)


# Параметры для инициализации обработчиков на уровне приложения
EVENTS_BUS = services.EventsBus(repo_factory)
VIEWER = services.Viewer(repo_factory)

# Параметры представления конечных данных
_START_YEAR = 2015
START_DATE: Final = datetime.date(_START_YEAR, 1, 1)
