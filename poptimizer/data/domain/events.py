"""Сообщения доменной области."""
from datetime import datetime
from typing import Dict, Optional, Tuple

from poptimizer.data.domain import model
from poptimizer.data.domain.services import tables, trading_day
from poptimizer.data.ports import base, events


class UpdateDataFrame(events.AbstractEvent):
    """Команда обновить DataFrame."""

    def __init__(self, table_name: base.TableName, force: bool = False):
        """Обновление может быть принудительным или по необходимости."""
        super().__init__()
        self._table_name = table_name
        self._force = force

    def handle_event(self, tables_dict: Dict[base.TableName, model.Table]) -> None:
        """Осуществляет выбор варианта обновления.

        - Принудительное
        - С помощью даты
        - С помощью вспомогательной таблицы
        """
        table_name = self._table_name
        force = self._force

        if force:
            self.new_events.append(UpdateTableByDate(table_name))
        elif (helper_name := tables.get_helper_name(self._table_name)) is None:
            end_of_trading_day = trading_day.potential_end()
            self.new_events.append(UpdateTableByDate(table_name, end_of_trading_day))
        else:
            self.new_events.append(UpdateTableWithHelper(table_name, helper_name))


class UpdateTableWithHelper(events.AbstractEvent):
    """Команда обновить с помощью вспомогательной таблицы."""

    def __init__(self, table_name: base.TableName, helper_name: base.TableName) -> None:
        """Для обновление нужно имена основной и вспомогательной таблиц."""
        super().__init__()
        self._table_name = table_name
        self._helper_name = helper_name

    @property
    def tables_required(self) -> Tuple[base.TableName, ...]:
        """Для обновления нужна сама таблица и вспомогательная."""
        return self._helper_name, self._table_name

    def handle_event(self, tables_dict: Dict[base.TableName, model.Table]) -> None:
        """Обновляет вспомогательную таблицу, а потом основную с учетом необходимости."""
        helper = tables_dict[self._helper_name]
        end_of_trading_day = trading_day.potential_end()
        if helper.need_update(end_of_trading_day):
            helper.update()

        main = tables_dict[self._table_name]
        end_of_trading_day = trading_day.real_end(helper)
        if main.need_update(end_of_trading_day):
            main.update()


class UpdateTableByDate(events.AbstractEvent):
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
    def tables_required(self) -> Tuple[base.TableName, ...]:
        """Для обновления таблицы требуется ее загрузка."""
        return (self._table_names,)

    def handle_event(self, tables_dict: Dict[base.TableName, model.Table]) -> None:
        """Обновляет таблицу.

        При отсутствии даты принудительно, а при наличии с учетом необходимости.
        """
        end = self._end_of_trading_day
        table = tables_dict[self._table_names]
        if end is None or table.need_update(end):
            table.update()
