"""Обработчики доменных событий."""
from typing import List

from poptimizer.data_di.domain import events, repos, tables
from poptimizer.data_di.shared import entities


class AppStartedHandler(entities.AbstractHandler[events.AppStarted]):
    """Запускает проверку окончания торгового дня."""

    def __init__(self, repo: repos.Repo[events.AppStarted]):
        """Сохраняет репо."""
        self._repo = repo

    async def handle_event(self, event: events.AppStarted) -> List[entities.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = tables.create_id("trading_date")
        table = await self._repo.get_table(table_id)
        return await table.handle_event(event)
