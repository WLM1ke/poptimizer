"""Базовая схема обновления."""
import abc
from datetime import datetime, timedelta

import pandas as pd
from pytz import timezone

from poptimizer.data.core import ports

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
END_HOUR = 0
END_MINUTE = 45


def end_of_trading_day() -> datetime:
    """Конец последнего торгового дня в UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)
    if end_of_trading > now:
        end_of_trading += timedelta(days=-1)
    end_of_trading = end_of_trading.astimezone(timezone("UTC"))
    return end_of_trading.replace(tzinfo=None)


class BaseUpdater(ports.AbstractUpdater):
    """Реализует базовую схему обновления после публикации информации об итогах торгов."""

    def need_update(self, timestamp: datetime) -> bool:
        """Нужно ли обновлять данные о диапазоне доступных торговых дат.

        Если последние обновление было раньше публикации данных о последних торгах, то требуется
        обновление.
        """
        if timestamp < end_of_trading_day():
            return True
        return False

    @abc.abstractmethod
    def get_update(self) -> pd.DataFrame:
        """Загружает обновление."""
