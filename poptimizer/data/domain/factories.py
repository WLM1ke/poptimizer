"""Фабрики по созданию объектов и их сериализации."""
from types import MappingProxyType

from poptimizer.data.adapters.loaders import (
    conomy,
    cpi,
    dividends,
    dohod,
    moex,
    smart_lab,
    trading_dates,
)
from poptimizer.data.domain import model
from poptimizer.data.ports import base, outer

# Описание групп таблиц
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


def create_table(name: base.TableName) -> model.Table:
    """Создает таблицу."""
    return model.Table(name=name, desc=_TABLES_REGISTRY[name.group])


def recreate_table(table_tuple: outer.TableTuple) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    name = base.TableName(table_tuple.group, table_tuple.name)
    return model.Table(name, _TABLES_REGISTRY[name.group], table_tuple.df, table_tuple.timestamp)


def convent_to_tuple(table: model.Table) -> outer.TableTuple:
    """Конвертирует объект в кортеж."""
    group, name = table.name
    if (timestamp := table.timestamp) is None:
        raise base.DataError(f"Попытка сериализации пустой таблицы {table.name}")
    return outer.TableTuple(group=group, name=name, df=table.df, timestamp=timestamp)
