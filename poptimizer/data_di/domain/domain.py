"""Конфигурация доменной модели."""
from typing import Callable, List, cast

import injector

from poptimizer.data_di.domain import repos, tables, trading_dates
from poptimizer.data_di.shared import entities, mapper

AnyTableFactory = tables.AbstractTableFactory[entities.AbstractEvent]


class Domain(injector.Module):
    """Конфигурация доменной модели."""

    @injector.multiprovider
    @injector.singleton
    def table_factories(
        self,
        trading_dates_factory: trading_dates.TablesFactory,
    ) -> List[AnyTableFactory]:
        """Перечень всех фабрик."""
        factories = [
            trading_dates_factory,
        ]
        return [cast(AnyTableFactory, factory) for factory in factories]

    @injector.provider
    @injector.singleton
    def repo_factory(
        self,
        db_session: mapper.MongoDBSession,
        factories: List[AnyTableFactory],
    ) -> Callable[[], repos.Repo]:
        return repos.ReposFactory(db_session, factories)
