"""Настройки модуля хранения данных."""
from typing import Type

from poptimizer.data.core.app import uow
from poptimizer.data.core.domain import model
from poptimizer.data.infrastructure import trading_dates


def register_all_tables() -> None:
    """Регистрация таблиц."""
    tables = {
        model.TableGroup("trading_dates"): model.TableSpec(updater=trading_dates.TradingDatesUpdater()),
    }
    model.registry.create_registry(tables)


def get_uow_factory() -> Type[uow.UnitOfWork]:
    """Регистрирует все типы таблиц и возвращает UoW со стандартным хранилищем данных."""
    register_all_tables()
    return uow.UnitOfWork
