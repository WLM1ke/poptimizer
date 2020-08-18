"""Спецификация таблицы с диапазоном торговых дат."""
import logging
from datetime import datetime, timedelta

import apimoex
import pandas as pd
from pytz import timezone

from poptimizer.data.core import ports
from poptimizer.data.infrastructure import connection

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
END_HOUR = 0
END_MINUTE = 45

logger = logging.getLogger(__name__)


def end_of_trading_day() -> datetime:
    """Конец последнего торгового дня в UTC."""
    now = datetime.now(MOEX_TZ)
    end_of_trading = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)
    if end_of_trading > now:
        end_of_trading += timedelta(days=-1)
    end_of_trading = end_of_trading.astimezone(timezone("UTC"))
    return end_of_trading.replace(tzinfo=None)


class TradingDatesUpdater(ports.AbstractUpdater):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def need_update(self, timestamp: datetime) -> bool:
        """Нужно ли обновлять данные о диапазоне доступных торговых дат.

        Если последние обновление было раньше публикации данных о последних торгах, то требуется
        обновление.
        """
        if timestamp < end_of_trading_day():
            return True
        return False

    def get_update(self) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        session = connection.get_http_session()
        json = apimoex.get_board_dates(session, board="TQBR", market="shares", engine="stock")
        logger.info(f"Последняя дата с историей: {json[0]['till']}")
        return pd.DataFrame(json)
