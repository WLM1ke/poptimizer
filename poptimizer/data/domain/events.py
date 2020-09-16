"""События, связанные с обновлением таблиц."""
import abc
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import pandas as pd

from poptimizer.data.domain import model, services
from poptimizer.data.ports import outer


class AbstractEvent(abc.ABC):
    """Абстрактный класс события."""


if TYPE_CHECKING:
    EventsQueue = asyncio.Queue[AbstractEvent]
else:
    EventsQueue = asyncio.Queue


class Command(AbstractEvent):
    """Абстрактный класс команды."""

    @property
    @abc.abstractmethod
    def table_required(self) -> Optional[outer.TableName]:
        """Перечень таблиц, которые нужны обработчику события."""

    @abc.abstractmethod
    async def handle_event(
        self,
        queue: EventsQueue,
        table: Optional[model.Table],
    ) -> None:
        """Обрабатывает событие и добавляет новые события в очередь."""


class GetDataFrame(Command):
    """Команда обновить DataFrame."""

    def __init__(self, table_name: outer.TableName, force: bool = False):
        """Обновление может быть принудительным или по необходимости."""
        super().__init__()
        self._table_name = table_name
        self._force = force

    @property
    def table_required(self) -> Optional[outer.TableName]:
        """Не требуется таблица."""

    async def handle_event(
        self,
        queue: EventsQueue,
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
            await queue.put(UpdateTable(table_name))
        elif (helper_name := services.get_helper_name(self._table_name)) is None:
            end_of_trading_day = services.trading_day_potential_end()
            await queue.put(UpdateTable(table_name, end_of_trading_day))
        else:
            await queue.put(GetEndOfTradingDay(table_name, helper_name))


class GetEndOfTradingDay(Command):
    """Узнает время окончания последних торгов."""

    def __init__(self, table_name: outer.TableName, helper_name: outer.TableName):
        """Хранит название обновляемой таблицы и вспомогательной таблицы с датами торгов."""
        super().__init__()
        self._table_name = table_name
        self._helper_name = helper_name

    @property
    def table_required(self) -> Optional[outer.TableName]:
        """Нужна вспомогательная таблица."""
        return self._helper_name

    async def handle_event(
        self,
        queue: EventsQueue,
        table: Optional[model.Table],
    ) -> None:
        """Узнает окончание рабочего дня и запрашивает обновление."""
        if table is None:
            raise outer.DataError("Нужна таблица")
        end_of_trading_day = services.trading_day_potential_end()
        await table.update(end_of_trading_day)
        end_of_trading_day = services.trading_day_real_end(table.df)
        await queue.put(UpdateTable(self._table_name, end_of_trading_day))


class UpdateTable(Command):
    """Команда обновить таблицу с учетом последней торговой даты."""

    def __init__(
        self,
        table_name: outer.TableName,
        end_of_trading_day: Optional[datetime] = None,
    ) -> None:
        """Обновляет таблицу с учетом конца торгового дня, а при отсутствии принудительно."""
        super().__init__()
        self._table_names = table_name
        self._end_of_trading_day = end_of_trading_day

    @property
    def table_required(self) -> outer.TableName:
        """Для обновления таблицы требуется ее загрузка."""
        return self._table_names

    async def handle_event(
        self,
        queue: EventsQueue,
        table: Optional[model.Table],
    ) -> None:
        """Обновляет таблицу и публикует результат.

        При отсутствии даты принудительно, а при наличии с учетом необходимости.
        """
        if table is None:
            raise outer.DataError("Нужна таблица")
        await table.update(self._end_of_trading_day)
        await queue.put(Result(table.name, table.df))


class Result(AbstractEvent):
    """Событие с результатом выполнения команды."""

    def __init__(self, name: outer.TableName, df: pd.DataFrame):
        """Имя и DataFrame с результатом."""
        self._name = name
        self._df = df

    @property
    def name(self) -> outer.TableName:
        """Имя таблицы."""
        return self._name

    @property
    def df(self) -> pd.DataFrame:
        """Результат в виде DataFrame."""
        return self._df
