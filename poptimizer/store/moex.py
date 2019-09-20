"""Менеджеры данных для котировок, индекса и перечня торгуемых бумаг с MOEX."""
from concurrent import futures
from datetime import datetime
from typing import Optional, Any, List, Dict

import apimoex

from poptimizer.config import POptimizerError
from poptimizer.store import manager
from poptimizer.store.db import MISC
from poptimizer.store.manager import AbstractManager
from poptimizer.store.utils import (
    DB,
    TICKER,
    REG_NUMBER,
    LOT_SIZE,
    DATE,
    OPEN,
    CLOSE,
    HIGH,
    LOW,
    TURNOVER,
)

# Наименование данных по акциям в коллекции misc
SECURITIES = "securities"

# Наименование данных по индексу в коллекции misc
INDEX = "MCFTRR"

# Наименование коллекции с котировками
QUOTES = "quotes"


class Securities(AbstractManager):
    """Информация о всех торгующихся акциях.

    При появлении новой информации создается с нуля, так как перечень торгуемых акций может как
    расширяться, так и сокращаться, а характеристики отдельных акций (например, размер лота) меняться
    со временем.
    """

    def __init__(self, db=DB) -> None:
        super().__init__(collection=MISC, db=db, create_from_scratch=True, index=TICKER)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает полностью данные о всех торгующихся акциях."""
        if item != SECURITIES:
            raise POptimizerError(
                f"Отсутствуют данные {self._collection.full_name}.{item}"
            )
        columns = ("SECID", "REGNUMBER", "LOTSIZE")
        data = apimoex.get_board_securities(self._session, columns=columns)
        formatters = dict(
            SECID=lambda x: (TICKER, x),
            REGNUMBER=lambda x: (REG_NUMBER, x),
            LOTSIZE=lambda x: (LOT_SIZE, x),
        )
        return manager.data_formatter(data, formatters)


class Index(AbstractManager):
    """Котировки индекса полной доходности с учетом российских налогов - MCFTRR."""

    def __init__(self, db=DB) -> None:
        super().__init__(collection=MISC, db=db)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Поддерживается частичная загрузка данных для обновления."""
        if item != INDEX:
            raise POptimizerError(
                f"Отсутствуют данные {self._collection.full_name}.{item}"
            )
        if last_index is not None:
            last_index = last_index.date()
        data = apimoex.get_board_history(
            self._session,
            start=last_index,
            security=INDEX,
            columns=("TRADEDATE", "CLOSE"),
            board="RTSI",
            market="index",
        )
        formatters = dict(
            TRADEDATE=lambda x: (DATE, datetime.strptime(x, "%Y-%m-%d")),
            CLOSE=lambda x: (CLOSE, x),
        )
        return manager.data_formatter(data, formatters)


class Quotes(AbstractManager):
    """Информация о котировках.

    Если у акции менялся тикер, но сохранялся регистрационный номер, то собирается полная история
    котировок для всех тикеров.
    """

    def __init__(self, db=DB) -> None:
        super().__init__(collection=QUOTES, db=db)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает полностью или только обновление по ценам HLOC и оборотам в рублях."""
        if last_index is None:
            aliases = self._find_aliases(item)
            data = self._download_many(aliases)
        else:
            data = apimoex.get_market_candles(
                self._session,
                item,
                start=last_index.date(),
                end=self.LAST_HISTORY_DATE.date(),
            )
        return self._formatter(data)

    def _find_aliases(self, ticker: str) -> List[str]:
        """Ищет все тикеры с эквивалентным регистрационным номером."""
        securities = Securities(self._collection.database.name)[SECURITIES]
        number = securities.at[ticker, REG_NUMBER]
        results = apimoex.find_securities(self._session, number)
        return [row["secid"] for row in results if row["regnumber"] == number]

    def _download_many(self, aliases: List[str]) -> List[Dict[str, Any]]:
        with futures.ThreadPoolExecutor(max_workers=len(aliases)) as executor:
            rez = [
                executor.submit(
                    apimoex.get_market_candles,
                    self._session,
                    ticker,
                    end=self.LAST_HISTORY_DATE.date(),
                )
                for ticker in aliases
            ]
            data = []
            for future in rez:
                data.extend(future.result())
        return self._clean_up(data)

    @staticmethod
    def _clean_up(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Преобразование данных для бумаг, которые торговались под разными тикерами и в разных режимах.

        Если торги шли в нескольких режимах, то данные могут быть не упорядочены.

        Иногда бывали параллельно торги для нескольких тикеров одной бумаги. Для таких случаев выбираем
        торги с большим оборотом.
        """
        data.sort(key=lambda x: (x["begin"], -x["value"]))
        data_clean = []
        for row in data:
            if not data_clean or data_clean[-1]["begin"] != row["begin"]:
                data_clean.append(row)
        return data_clean

    @staticmethod
    def _formatter(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatters = dict(
            begin=lambda x: (DATE, datetime.strptime(x, "%Y-%m-%d %H:%M:%S")),
            open=lambda x: (OPEN, x),
            close=lambda x: (CLOSE, x),
            high=lambda x: (HIGH, x),
            low=lambda x: (LOW, x),
            value=lambda x: (TURNOVER, x),
        )
        return manager.data_formatter(data, formatters)
