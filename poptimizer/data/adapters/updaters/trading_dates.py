"""Спецификация таблицы с диапазоном торговых дат."""
import apimoex
import pandas as pd

from poptimizer.data import ports
from poptimizer.data.adapters import connection
from poptimizer.data.adapters.updaters import updater


class TradingDatesUpdater(updater.BaseUpdater):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def __call__(self, table_name: ports.TableName) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        name = self._log_and_validate_group(table_name, ports.TRADING_DATES)
        if name != ports.TRADING_DATES:
            raise ports.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        session = connection.get_http_session()
        json = apimoex.get_board_dates(session, board="TQBR", market="shares", engine="stock")
        self._logger.info(f"Последняя дата с историей: {json[0]['till']}")
        return pd.DataFrame(json)
