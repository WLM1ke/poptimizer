"""Спецификация таблицы с диапазоном торговых дат."""
import apimoex
import pandas as pd

from poptimizer.data.adapters.updaters import connection, logger
from poptimizer.data.ports import base, outer


class TradingDatesUpdater(logger.LoggerMixin, outer.AbstractUpdater):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        name = self._log_and_validate_group(table_name, base.TRADING_DATES)
        if name != base.TRADING_DATES:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        session = connection.get_http_session()
        json = apimoex.get_board_dates(session, board="TQBR", market="shares", engine="stock")
        self._logger.info(f"Последняя дата с историей: {json[0]['till']}")
        return pd.DataFrame(json)
