"""Проверка необходимости осуществления обновления таблицы."""
from datetime import datetime, timedelta, timezone
from typing import Final, Optional

import pandas as pd

from poptimizer.data.ports import base

# Часовой пояс MOEX
MOEX_TZ: Final = timezone(timedelta(hours=3))

# Торги заканчиваются в 24.00, но данные публикуются 00.45
END_HOUR: Final = 0
END_MINUTE: Final = 45


def _to_utc_naive(date: datetime) -> datetime:
    """Переводит дату в UTC и делает ее наивной."""
    date = date.astimezone(timezone.utc)
    return date.replace(tzinfo=None)


def trading_day_potential_end() -> datetime:
    """Конец возможного последнего торгового дня UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(hour=END_HOUR, minute=END_MINUTE)
    if end_of_trading > now:
        end_of_trading -= timedelta(days=1)
    return _to_utc_naive(end_of_trading)


def trading_day_real_end(df: pd.DataFrame) -> datetime:
    """Конец реального (с имеющейся историей) торгового дня UTC."""
    last_trading_day = df.loc[0, "till"]
    end_of_trading = last_trading_day.replace(
        hour=END_HOUR,
        minute=END_MINUTE,
        tzinfo=MOEX_TZ,
    )
    end_of_trading += timedelta(days=1)
    return _to_utc_naive(end_of_trading)


def get_helper_name(name: base.TableName) -> Optional[base.TableName]:
    """Имя вспомогательной таблицы."""
    if name.group != base.TRADING_DATES:
        return base.TableName(base.TRADING_DATES, base.TRADING_DATES)
    return None
