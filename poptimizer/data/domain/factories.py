"""Фабрики по созданию таблиц и их сериализации."""
from types import MappingProxyType

from poptimizer.data.adapters.loaders import (
    bcs,
    conomy,
    cpi,
    dividends,
    dohod,
    moex,
    smart_lab,
    trading_dates,
)
from poptimizer.data.domain import model
from poptimizer.data.ports import outer

# Описание групп таблиц
_TRADING_DATES = model.TableDescription(
    loader=trading_dates.TradingDatesLoader(),
    index_checks=model.IndexChecks.NO_CHECKS,
    validate=False,
)
_CONOMY = model.TableDescription(
    loader=conomy.ConomyLoader(),
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_BCS = model.TableDescription(
    loader=bcs.BCS(),
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_DOHOD = model.TableDescription(
    loader=dohod.DohodLoader(),
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_SMART_LAB = model.TableDescription(
    loader=smart_lab.SmartLabLoader(),
    index_checks=model.IndexChecks.NO_CHECKS,
    validate=False,
)
_DIVIDENDS = model.TableDescription(
    loader=dividends.DividendsLoader(),
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_CPI = model.TableDescription(
    loader=cpi.CPILoader(),
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)
_SECURITIES_LOADER = moex.SecuritiesLoader()
_SECURITIES = model.TableDescription(
    loader=_SECURITIES_LOADER,
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=False,
)
_INDEX = model.TableDescription(
    loader=moex.IndexLoader(),
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)
_QUOTES = model.TableDescription(
    loader=moex.QuotesLoader(_SECURITIES_LOADER),
    index_checks=model.IndexChecks.UNIQUE_ASCENDING,
    validate=True,
)
_TABLES_REGISTRY = MappingProxyType(
    {
        outer.TRADING_DATES: _TRADING_DATES,
        outer.CONOMY: _CONOMY,
        outer.BCS: _BCS,
        outer.DOHOD: _DOHOD,
        outer.SMART_LAB: _SMART_LAB,
        outer.DIVIDENDS: _DIVIDENDS,
        outer.CPI: _CPI,
        outer.SECURITIES: _SECURITIES,
        outer.INDEX: _INDEX,
        outer.QUOTES: _QUOTES,
    },
)


def create_table(name: outer.TableName) -> model.Table:
    """Создает пустую новую таблицу."""
    return model.Table(name=name, desc=_TABLES_REGISTRY[name.group])


def recreate_table(table_tuple: outer.TableTuple) -> model.Table:
    """Создает таблицу на основе данных и обновляет ее."""
    name = outer.TableName(table_tuple.group, table_tuple.name)
    return model.Table(name, _TABLES_REGISTRY[name.group], table_tuple.df, table_tuple.timestamp)


def convent_to_tuple(table: model.Table) -> outer.TableTuple:
    """Конвертирует таблицу в кортеж."""
    group, name = table.name
    if (timestamp := table.timestamp) is None:
        raise outer.DataError(f"Попытка сериализации пустой таблицы {table.name}")
    return outer.TableTuple(group=group, name=name, df=table.df, timestamp=timestamp)
