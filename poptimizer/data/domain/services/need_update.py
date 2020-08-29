"""Проверка необходимости осуществления обновления таблицы."""
from datetime import datetime, timedelta

from pytz import timezone

from poptimizer.data.domain import model
from poptimizer.data.ports import base

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
END_HOUR = 0
END_MINUTE = 45


def _to_utc_naive(date: datetime) -> datetime:
    """Переводит дату в UTC и делает ее наивной."""
    date = date.astimezone(timezone("UTC"))
    return date.replace(tzinfo=None)


def potential_end() -> datetime:
    """Конец возможного последнего торгового дня UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)
    if end_of_trading > now:
        end_of_trading += timedelta(days=-1)
    return _to_utc_naive(end_of_trading)


def real_end(helper_table: model.Table) -> datetime:
    """Конец реального (с имеющейся историей) торгового дня UTC."""
    df = helper_table.df
    if df is None:
        raise base.DataError(f"Некорректная вспомогательная таблица {helper_table}")
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
    return table.helper_table is None and timestamp < potential_end()


def rule_for_new_or_with_helper(table: model.Table) -> bool:
    """Правило обновления для таблиц с вспомогательной таблицей.

    - Если новая, то есть не содержит данных
    - Не обновлялась после реального окончания последнего торгового дня из вспомогательной таблицы
    """
    if (timestamp := table.timestamp) is None:
        return True
    return table.helper_table is not None and timestamp < real_end(table.helper_table)


def check(table: model.Table) -> bool:
    """Нужно ли обновлять данные о диапазоне доступных торговых дат.

    Если последние обновление было раньше публикации данных о последних торгах, то требуется
    обновление.
    """
    check_func = (
        rule_for_new_or_without_helper,
        rule_for_new_or_with_helper,
    )
    return any(func(table) for func in check_func)
