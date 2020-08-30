"""Загрузка данных с MOEX."""
import apimoex
import pandas as pd

from poptimizer.data.adapters.updaters import connection, updater
from poptimizer.data.ports import base, names


class SecuritiesUpdater(updater.BaseUpdater):
    """Информация о всех торгующихся акциях."""

    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        name = self._log_and_validate_group(table_name, base.SECURITIES)
        if name != base.SECURITIES:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        columns = ("SECID", "REGNUMBER", "LOTSIZE")
        json = apimoex.get_board_securities(connection.get_http_session(), columns=columns)
        df = pd.DataFrame(json)
        df.columns = [names.TICKER, names.REG_NUMBER, names.LOT_SIZE]
        return df.set_index(names.TICKER)
