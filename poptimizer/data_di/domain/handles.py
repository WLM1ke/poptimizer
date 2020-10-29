"""Обработчики доменных событий."""
from typing import List

from injector import Inject

from poptimizer.data_di.domain import events, repos
from poptimizer.data_di.shared import entity


class AppStartedHandler(entity.AbstractHandler[events.AppStarted]):
    """Запускает проверку окончания торгового дня."""

    def __init__(self, repo: Inject[repos.Repo]):
        """Сохраняет репо."""
        self._repo = repo

    async def handle_event(self, event: events.AppStarted) -> List[entity.AbstractEvent]:
        """Обновляет таблицу с торговыми днями."""
        table_id = repos.create_id("trading_date")
        table = await self._repo.get_table(table_id)
        return await table.handle_event(event)
