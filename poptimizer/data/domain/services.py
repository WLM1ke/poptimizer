"""Проверка необходимости осуществления обновления таблицы."""
from datetime import datetime, timedelta, timezone
from typing import Final, Optional

import pandas as pd

from poptimizer.data.domain import events, repo
from poptimizer.data.ports import outer

# Часовой пояс MOEX
MOEX_TZ: Final = timezone(timedelta(hours=3))

# Торги заканчиваются в 24.00, но данные публикуются 00.45
END_HOUR: Final = 0
END_MINUTE: Final = 45


def _to_utc_naive(date: datetime) -> datetime:
    """Переводит дату в UTC и делает ее наивной."""
    date = date.astimezone(timezone.utc)
    return date.replace(tzinfo=None)


def _trading_day_potential_end() -> datetime:
    """Конец возможного последнего торгового дня UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(
        hour=END_HOUR,
        minute=END_MINUTE,
        second=0,
        microsecond=0,
    )
    if end_of_trading > now:
        end_of_trading -= timedelta(days=1)
    return _to_utc_naive(end_of_trading)


def _trading_day_real_end(df: pd.DataFrame) -> datetime:
    """Конец реального (с имеющейся историей) торгового дня UTC."""
    last_trading_day = df.loc[0, "till"]
    end_of_trading = last_trading_day.replace(
        hour=END_HOUR,
        minute=END_MINUTE,
        second=0,
        microsecond=0,
        tzinfo=MOEX_TZ,
    )
    end_of_trading += timedelta(days=1)
    return _to_utc_naive(end_of_trading)


def _get_helper_name(name: outer.TableName) -> Optional[outer.TableName]:
    """Имя вспомогательной таблицы."""
    if name.group != outer.TRADING_DATES:
        return outer.TableName(outer.TRADING_DATES, outer.TRADING_DATES)
    return None


async def select_update_type(
    queue: events.EventsQueue,
    _: repo.Repo,
    event: events.AbstractEvent,
) -> None:
    """Выбирает способ обновления таблицы."""
    if not isinstance(event, events.UpdatedDfRequired):
        raise outer.DataError("Неверный тип события")

    table_name = event.table_name
    if event.force:
        await queue.put(events.UpdateWithTimestampRequired(table_name))
    elif (helper_name := _get_helper_name(table_name)) is None:
        end_of_trading_day = _trading_day_potential_end()
        await queue.put(events.UpdateWithTimestampRequired(table_name, end_of_trading_day))
    else:
        await queue.put(events.UpdateWithHelperRequired(table_name, helper_name))


async def update_with_helper(
    queue: events.EventsQueue,
    store: repo.Repo,
    event: events.AbstractEvent,
) -> None:
    """Получает отметку времени из вспомогательной таблицы для обновления основной таблицы."""
    if not isinstance(event, events.UpdateWithHelperRequired):
        raise outer.DataError("Неверный тип события")

    end_of_trading_day = _trading_day_potential_end()
    helper = await repo.load_or_create_table(store, event.helper_name)
    await helper.update(end_of_trading_day)

    end_of_trading_day = _trading_day_real_end(helper.df)
    await queue.put(events.UpdateWithTimestampRequired(event.table_name, end_of_trading_day))


async def update_with_timestamp(
    queue: events.EventsQueue,
    store: repo.Repo,
    event: events.AbstractEvent,
) -> None:
    """Обновляет таблицу для получения корректных данных."""
    if not isinstance(event, events.UpdateWithTimestampRequired):
        raise outer.DataError("Неверный тип события")
    table = await repo.load_or_create_table(store, event.table_name)
    await table.update(event.timestamp)
    await queue.put(events.Result(table.name, table.df))
