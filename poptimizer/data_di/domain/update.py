"""Политики обновления таблиц."""
from datetime import datetime, timedelta, timezone
from typing import Final, Optional

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
    """Возможный конец последнего торгового дня UTC."""
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


def trading_day_potential_end_policy(last_update: Optional[datetime]) -> bool:
    """Конец возможного последнего торгового дня UTC."""
    if last_update is None:
        return True
    if _trading_day_potential_end() > last_update:
        return True
    return False
