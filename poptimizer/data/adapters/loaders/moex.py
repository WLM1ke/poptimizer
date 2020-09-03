"""Загрузка данных с MOEX."""
import datetime
from typing import List, Optional, cast

import apimoex
import pandas as pd
from pytz import timezone

from poptimizer.data.adapters.loaders import connection, logger
from poptimizer.data.ports import base, col

# Часовой пояс MOEX
MOEX_TZ = timezone("Europe/Moscow")


class SecuritiesLoader(logger.LoggerMixin, base.AbstractLoader):
    """Информация о всех торгующихся акциях."""

    def __call__(self, table_name: base.TableName) -> pd.DataFrame:
        """Получение списка торгуемых акций с регистрационным номером и размером лота."""
        name = self._log_and_validate_group(table_name, base.SECURITIES)
        if name != base.SECURITIES:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        columns = ("SECID", "REGNUMBER", "LOTSIZE")
        json = apimoex.get_board_securities(connection.get_http_session(), columns=columns)
        df = pd.DataFrame(json)
        df.columns = [col.TICKER, col.REG_NUMBER, col.LOT_SIZE]
        return df.set_index(col.TICKER)


class IndexLoader(logger.LoggerMixin, base.AbstractIncrementalLoader):
    """Котировки индекса полной доходности с учетом российских налогов - MCFTRR."""

    def __call__(
        self,
        table_name: base.TableName,
        start_date: Optional[datetime.date] = None,
    ) -> pd.DataFrame:
        """Получение цен закрытия индекса MCFTRR."""
        name = self._log_and_validate_group(table_name, base.INDEX)
        if name != base.INDEX:
            raise base.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        json = apimoex.get_board_history(
            session=connection.get_http_session(),
            start=str(start_date),
            security=base.INDEX,
            columns=("TRADEDATE", "CLOSE"),
            board="RTSI",
            market="index",
        )
        df = pd.DataFrame(json)
        df.columns = [col.DATE, col.CLOSE]
        df[col.DATE] = pd.to_datetime(df[col.DATE])
        return df.set_index(col.DATE)


def _previous_day_in_moscow() -> str:
    """Предыдущий день в Москве.

    Необходим для ограничения скачивания промежуточных свечек в последний день.
    """
    date = datetime.datetime.now(MOEX_TZ)
    date += datetime.timedelta(days=-1)
    return str(date.date())


def _download_many(aliases: List[str]) -> pd.DataFrame:
    """Загрузка нескольких рядов котировок."""
    http_session = connection.get_http_session()
    json_all_aliases = []
    for ticker in aliases:
        json = apimoex.get_market_candles(http_session, ticker, end=_previous_day_in_moscow())
        json_all_aliases.extend(json)

    df = pd.DataFrame(json_all_aliases)
    df = df.sort_values(by=["begin", "value"])
    return df.groupby("begin", as_index=False).last()


class QuotesLoader(logger.LoggerMixin, base.AbstractIncrementalLoader):
    """Котировки акций."""

    def __init__(self) -> None:
        """Кэшируются вспомогательные данные, чтобы сократить количество обращений к серверу MOEX."""
        super().__init__()
        self._securities_cache = None

    def __call__(
        self,
        table_name: base.TableName,
        start_date: Optional[datetime.date] = None,
    ) -> pd.DataFrame:
        """Получение котировок акций в формате OCHLV."""
        ticker = self._log_and_validate_group(table_name, base.QUOTES)

        if start_date is None:
            aliases = self._find_aliases(ticker)
            df = _download_many(aliases)
        else:
            json = apimoex.get_market_candles(
                connection.get_http_session(),
                ticker,
                start=str(start_date),
                end=_previous_day_in_moscow(),
            )
            df = pd.DataFrame(json)

        df.columns = [
            col.DATE,
            col.OPEN,
            col.CLOSE,
            col.HIGH,
            col.LOW,
            col.TURNOVER,
        ]
        df[col.DATE] = pd.to_datetime(df[col.DATE])
        return df.set_index(col.DATE)

    def _find_aliases(self, ticker: str) -> List[str]:
        """Ищет все тикеры с эквивалентным регистрационным номером."""
        number = self._get_reg_num(ticker)
        json = apimoex.find_securities(connection.get_http_session(), number)
        return [row["secid"] for row in json if row["regnumber"] == number]

    def _get_reg_num(self, ticker: str) -> str:
        df = self._securities_cache
        if df is None:
            loader = SecuritiesLoader()
            table_name = base.TableName(base.SECURITIES, base.SECURITIES)
            df = loader(table_name)
            self._securities_cache = df

        return cast(str, df.at[ticker, col.REG_NUMBER])
