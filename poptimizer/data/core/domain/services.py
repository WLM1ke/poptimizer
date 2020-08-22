"""Доменные службы, ответственные за обновление таблиц."""
from datetime import datetime, timedelta

from pytz import timezone

from poptimizer.data.core import ports
from poptimizer.data.core.domain import model

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
END_HOUR = 0
END_MINUTE = 45


def _end_of_trading_day() -> datetime:
    """Конец последнего торгового дня в UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)
    if end_of_trading > now:
        end_of_trading += timedelta(days=-1)
    end_of_trading = end_of_trading.astimezone(timezone("UTC"))
    return end_of_trading.replace(tzinfo=None)


def need_update(table: model.Table) -> bool:
    """Нужно ли обновлять данные о диапазоне доступных торговых дат.

    Если последние обновление было раньше публикации данных о последних торгах, то требуется
    обновление.
    """
    if (timestamp := table.timestamp) is None or timestamp < _end_of_trading_day():
        return True
    return False


def update_table(table: model.Table, updater: ports.AbstractUpdater) -> None:
    """Обновляет таблицу."""
    if not need_update(table):
        return None
    df = updater.get_update()
    table.df = df
