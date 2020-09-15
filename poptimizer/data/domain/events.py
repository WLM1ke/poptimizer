"""События, связанные с обновлением таблиц."""
from datetime import datetime
from typing import Optional

from poptimizer.data.domain import model, services
from poptimizer.data.ports import base, outer
from poptimizer.data.ports.outer import EventsQueue


class UpdateChecked(outer.AbstractEvent):
    """Команда обновить DataFrame."""

    def __init__(self, table_name: base.TableName, force: bool = False):
        """Обновление может быть принудительным или по необходимости."""
        super().__init__()
        self._table_name = table_name
        self._force = force

    @property
    def table_required(self) -> Optional[base.TableName]:
        """Не требуется таблица."""

    async def handle_event(
        self,
        queue: outer.EventsQueue,
        table: Optional[model.Table],
    ) -> None:
        """Осуществляет выбор варианта обновления.

        - Принудительное
        - С помощью даты
        - С помощью вспомогательной таблицы
        """
        table_name = self._table_name
        force = self._force

        if force:
            await queue.put(TradingDateLoaded(table_name))
        elif (helper_name := services.get_helper_name(self._table_name)) is None:
            end_of_trading_day = services.trading_day_potential_end()
            await queue.put(TradingDateLoaded(table_name, end_of_trading_day))
        else:
            await queue.put(TradingDayEndRequired(table_name, helper_name))


class TradingDayEndRequired(outer.AbstractEvent):
    """Узнает время окончания последних торгов."""

    def __init__(self, table_name: base.TableName, helper_name: base.TableName):
        """Хранит название обновляемой таблицы и вспомогательной таблицы с датами торгов."""
        super().__init__()
        self._table_name = table_name
        self._helper_name = helper_name

    @property
    def table_required(self) -> Optional[base.TableName]:
        """Нужна вспомогательная таблица."""
        return self._helper_name

    async def handle_event(
        self,
        queue: EventsQueue,
        table: Optional[model.Table],
    ) -> None:
        """Узнает окончание рабочего дня и запрашивает обновление."""
        if table is None:
            raise base.DataError("Нужна таблица")
        end_of_trading_day = services.trading_day_potential_end()
        await table.update(end_of_trading_day)
        end_of_trading_day = services.trading_day_real_end(table.df)
        await queue.put(TradingDateLoaded(self._table_name, end_of_trading_day))


class TradingDateLoaded(outer.AbstractEvent):
    """Команда обновить таблицу с учетом последней торговой даты."""

    def __init__(
        self,
        table_name: base.TableName,
        end_of_trading_day: Optional[datetime] = None,
    ) -> None:
        """Обновляет таблицу с учетом конца торгового дня, а при отсутствии принудительно."""
        super().__init__()
        self._table_names = table_name
        self._end_of_trading_day = end_of_trading_day

    @property
    def table_required(self) -> base.TableName:
        """Для обновления таблицы требуется ее загрузка."""
        return self._table_names

    async def handle_event(
        self,
        queue: outer.EventsQueue,
        table: Optional[model.Table],
    ) -> None:
        """Обновляет таблицу.

        При отсутствии даты принудительно, а при наличии с учетом необходимости.
        """
        if table is None:
            raise base.DataError("Нужна таблица")
        await table.update(self._end_of_trading_day)
