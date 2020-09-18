"""События, связанные с обновлением таблиц."""
import abc
import asyncio
import dataclasses
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import pandas as pd

from poptimizer.data.ports import outer


@dataclasses.dataclass
class AbstractEvent(abc.ABC):
    """Абстрактный класс события."""

    table_name: outer.TableName


if TYPE_CHECKING:
    EventsQueue = asyncio.Queue[AbstractEvent]
else:
    EventsQueue = asyncio.Queue


@dataclasses.dataclass
class UpdatedDfRequired(AbstractEvent):
    """Требуется обновленный DataFrame."""

    force: bool = False


@dataclasses.dataclass
class UpdateWithHelperRequired(AbstractEvent):
    """Требуется обновление с помощью вспомогательной таблицы."""

    helper_name: outer.TableName


@dataclasses.dataclass
class UpdateWithTimestampRequired(AbstractEvent):
    """Требуется обновление с помощью отметка времени последних торгов."""

    timestamp: Optional[datetime] = None


@dataclasses.dataclass
class Result(AbstractEvent):
    """Событие с результатом выполнения команды."""

    df: pd.DataFrame
