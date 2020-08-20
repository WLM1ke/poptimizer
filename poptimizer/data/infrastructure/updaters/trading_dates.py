"""Спецификация таблицы с диапазоном торговых дат."""
import logging

import apimoex
import pandas as pd

from poptimizer.data.core import ports
from poptimizer.data.infrastructure import connection

logger = logging.getLogger(__name__)


class TradingDatesUpdater(ports.AbstractUpdater):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def get_update(self) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        session = connection.get_http_session()
        json = apimoex.get_board_dates(session, board="TQBR", market="shares", engine="stock")
        logger.info(f"Последняя дата с историей: {json[0]['till']}")
        return pd.DataFrame(json)
