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


def _end_of_potential_trading_day() -> datetime:
    """Конец возможного последнего торгового дня UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)
    if end_of_trading > now:
        end_of_trading += timedelta(days=-1)
    return _to_utc_naive(end_of_trading)


def _end_of_real_trading_day(helper_table: model.Table) -> datetime:
    """Конец реального (с имеющейся историей) торгового дня UTC."""
    df = helper_table.df
    if df is None:
        raise ports.DataError(f"Некорректная вспомогательная таблица {helper_table}")
    date_str = df.loc[0, "till"]
    date = datetime.strptime(date_str, "%Y-%m-%d")  # noqa: WPS323
    date = date.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0, tzinfo=MOEX_TZ)
    date = date + timedelta(days=1)
    return _to_utc_naive(date)


def rule_for_new_or_without_helper(table: model.Table) -> bool:
    """Правило обновления для таблиц без вспомогательной таблицы.

    - Если новая, то есть не содержит данных
    - Не обновлялась после возможного окончания последнего торгового дня
    """
    if (timestamp := table.timestamp) is None:
        return True
    return table.helper_table is None and timestamp < _end_of_potential_trading_day()


def rule_for_new_or_with_helper(table: model.Table) -> bool:
    """Правило обновления для таблиц с вспомогательной таблицей.

    - Если новая, то есть не содержит данных
    - Не обновлялась после реального окончания последнего торгового дня из вспомогательной таблицы
    """
    if (timestamp := table.timestamp) is None:
        return True
    return table.helper_table is not None and timestamp < _end_of_real_trading_day(table.helper_table)


def need_update(table: model.Table) -> bool:
    """Нужно ли обновлять данные о диапазоне доступных торговых дат.

    Если последние обновление было раньше публикации данных о последних торгах, то требуется
    обновление.
    """
    check_func = (
        rule_for_new_or_without_helper,
        rule_for_new_or_with_helper,
    )
    return any(func(table) for func in check_func)


def update_table(table: model.Table, registry: ports.AbstractUpdatersRegistry) -> None:
    """Обновляет таблицу."""
    if (helper_table := table.helper_table) is not None:
        update_table(helper_table, registry)
    if need_update(table):
        updater = registry[table.name.group]
        df = updater(table.name)
        table.df = df
