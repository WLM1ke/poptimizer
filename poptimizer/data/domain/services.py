"""Доменные службы, ответственные за обновление таблиц."""
from datetime import datetime, timedelta

from pytz import timezone

from poptimizer.data import ports
from poptimizer.data.domain import model

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
END_HOUR = 0
END_MINUTE = 45


def _to_utc_naive(date: datetime) -> datetime:
    """Переводит дату в UTC и делает ее наивной."""
    date = date.astimezone(timezone("UTC"))
    return date.replace(tzinfo=None)


def _end_of_trading_day() -> datetime:
    """Конец последнего торгового дня в UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)
    if end_of_trading > now:
        end_of_trading += timedelta(days=-1)
    return _to_utc_naive(end_of_trading)


def _last_history_date(helper_table: model.Table) -> datetime:
    """Момент времени UTC публикации информации о последних торгах."""
    df = helper_table.df
    if df is None:
        raise ports.DataError(f"Некорректная вспомогательная таблица {helper_table}")
    date_str = df.loc[0, "till"]
    date = datetime.strptime(date_str, "%Y-%m-%d")  # noqa: WPS323
    date = date.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0, tzinfo=MOEX_TZ)
    date = date + timedelta(days=1)
    return _to_utc_naive(date)


def need_update(table: model.Table) -> bool:
    """Нужно ли обновлять данные о диапазоне доступных торговых дат.

    Если последние обновление было раньше публикации данных о последних торгах, то требуется
    обновление.
    """
    timestamp = table.timestamp
    if timestamp is None:
        return True
    if (helper_table := table.helper_table) is not None:
        if timestamp < _last_history_date(helper_table):
            return True
    elif timestamp < _end_of_trading_day():
        return True
    return False


def update_table(table: model.Table, registry: ports.AbstractUpdatersRegistry) -> None:
    """Обновляет таблицу."""
    if (helper_table := table.helper_table) is not None:
        update_table(helper_table, registry)
    if need_update(table):
        updater = registry[table.name.group]
        df = updater(table.name)
        table.df = df
