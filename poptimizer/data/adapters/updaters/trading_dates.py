"""Спецификация таблицы с диапазоном торговых дат."""
import apimoex
import pandas as pd

from poptimizer.data import ports
from poptimizer.data.adapters import connection
from poptimizer.data.adapters.updaters import updater


class TradingDatesUpdater(updater.BaseUpdater):
    """Обновление для таблиц с диапазоном доступных торговых дат."""

    def __call__(self, name: ports.TableName) -> pd.DataFrame:
        """Получение обновленных данных о доступном диапазоне торговых дат."""
        if name != ports.TableName(ports.TRADING_DATES, ports.TRADING_DATES):
            raise ports.DataError(f"Некорректное имя таблицы для обновления {name}")
        self._logger.info(f"Загрузка данных: {name}")
        session = connection.get_http_session()
        json = apimoex.get_board_dates(session, board="TQBR", market="shares", engine="stock")
        self._logger.info(f"Последняя дата с историей: {json[0]['till']}")
        return pd.DataFrame(json)
