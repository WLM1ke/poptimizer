"""Менеджеры данных для котировок, индекса и перечня торгуемых бумаг с MOEX."""
from concurrent import futures
from datetime import datetime
from typing import Optional, Any, List, Dict

import apimoex

from poptimizer.config import POptimizerError
from poptimizer.store import utils_new, manager_new
from poptimizer.store.manager_new import AbstractManager

# Наименование данных по акциям
SECURITIES = "securities"

# Наименование данных по индексу
INDEX = "MCFTRR"

# Наименование коллекции с котировками
QUOTES = "quotes"


class Securities(AbstractManager):
    """Информация о всех торгующихся акциях.

    При появлении новой информации создается с нуля, так как перечень торгуемых акций может как
    расширяться, так и сокращаться, а характеристики отдельных акций (например, размер лота) меняться
    со временем.
    """

    def __init__(self, db=utils_new.DB) -> None:
        super().__init__(
            collection=utils_new.MISC,
            db=db,
            create_from_scratch=True,
            index=utils_new.TICKER,
        )

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает полностью данные о всех торгующихся акциях."""
        if item != SECURITIES:
            raise POptimizerError(
                f"Отсутствуют данные {self._collection.full_name}.{item}"
            )
        columns = ("SECID", "REGNUMBER", "LOTSIZE")
        data = apimoex.get_board_securities(self._session, columns=columns)
        formatters = dict(
            SECID=lambda x: (utils_new.TICKER, x),
            REGNUMBER=lambda x: (utils_new.REG_NUMBER, x),
            LOTSIZE=lambda x: (utils_new.LOT_SIZE, x),
        )
        return manager_new.data_formatter(data, formatters)


class Index(AbstractManager):
    """Котировки индекса полной доходности с учетом российских налогов - MCFTRR."""

    REQUEST_PARAMS = dict(
        security=INDEX, columns=("TRADEDATE", "CLOSE"), board="RTSI", market="index"
    )

    def __init__(self, db=utils_new.DB) -> None:
        super().__init__(collection=utils_new.MISC, db=db)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Поддерживается частичная загрузка данных для обновления."""
        if item != INDEX:
            raise POptimizerError(
                f"Отсутствуют данные {self._collection.full_name}.{item}"
            )
        data = apimoex.get_board_history(
            self._session, start=last_index.date(), **self.REQUEST_PARAMS
        )
        formatters = dict(
            TRADEDATE=lambda x: (utils_new.DATE, datetime.strptime(x, "%Y-%m-%d")),
            CLOSE=lambda x: (utils_new.CLOSE, x),
        )
        return manager_new.data_formatter(data, formatters)


class Quotes(AbstractManager):
    """Информация о котировках.

    Если у акции менялся тикер, но сохранялся регистрационный номер, то собирается полная история
    котировок для всех тикеров в режиме TQBR.
    """

    def __init__(self, db=utils_new.DB) -> None:
        super().__init__(collection=QUOTES, db=db)

    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает полностью или только обновление по ценам закрытия и оборотам в рублях."""
        if last_index is None:
            aliases = self._find_aliases(item)
        else:
            aliases = [item]
        if len(aliases) == 1:
            data = apimoex.get_board_candles(
                self._session,
                item,
                start=last_index.date(),
                end=self.LAST_HISTORY_DATE.date(),
            )
        else:
            data = self._download_many(aliases)
        return self._formatter(data)

    def _find_aliases(self, ticker: str) -> List[str]:
        """Ищет все тикеры с эквивалентным регистрационным номером в режиме TQBR."""
        securities = Securities(self._collection.database.name)[SECURITIES]
        number = securities.at[ticker, utils_new.REG_NUMBER]
        results = apimoex.find_securities(
            self._session, number, columns=("secid", "regnumber", "primary_boardid")
        )
        return [
            row["secid"]
            for row in results
            if row["regnumber"] == number and row["primary_boardid"] == "TQBR"
        ]

    def _download_many(self, aliases: List[str]) -> List[Dict[str, Any]]:
        with futures.ThreadPoolExecutor(max_workers=len(aliases)) as executor:
            rez = [
                executor.submit(
                    apimoex.get_board_candles,
                    self._session,
                    ticker,
                    end=self.LAST_HISTORY_DATE.date(),
                )
                for ticker in aliases
            ]
            data = []
            for future in rez:
                data.extend(future.result())
        data.sort(key=lambda x: x["begin"])
        return data

    @staticmethod
    def _formatter(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatters = dict(
            open=lambda x: (utils_new.OPEN, x),
            close=lambda x: (utils_new.CLOSE, x),
            high=lambda x: (utils_new.HIGH, x),
            low=lambda x: (utils_new.LOW, x),
            value=lambda x: (utils_new.TURNOVER, x),
            volume=lambda x: (utils_new.AMOUNT, x),
            begin=lambda x: (utils_new.DATE, datetime.strptime(x, "%Y-%m-%d %H:%M:%S")),
            end=lambda x: (
                utils_new.DATE_END,
                datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
            ),
        )
        return manager_new.data_formatter(data, formatters)
