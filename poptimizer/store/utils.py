"""Вспомогательные функции для хранения данных."""
import logging
from datetime import datetime
from typing import Tuple, Dict, Any

import apimoex
import pandas as pd

from poptimizer.store import mongo, database
from poptimizer.store.mongo import DB, MISC

# Метки столбцов данных
DATE = "DATE"
OPEN = "OPEN"
CLOSE = "CLOSE"
HIGH = "HIGH"
LOW = "LOW"
TURNOVER = "TURNOVER"
TICKER = "TICKER"
REG_NUMBER = "REG_NUMBER"
LOT_SIZE = "LOT_SIZE"
DIVIDENDS = "DIVIDENDS"

# Часовой пояс MOEX
MOEX_TZ = "Europe/Moscow"

# Торги заканчиваются в 19.00, но данные публикуются 19.45
END_OF_TRADING = dict(hour=19, minute=45, second=0, microsecond=0, nanosecond=0)


def now_and_end_of_trading_day() -> Tuple[datetime, datetime]:
    """Конец последнего торгового дня в UTC."""
    now = pd.Timestamp.now(MOEX_TZ)
    end_of_trading = now.replace(**END_OF_TRADING)
    if end_of_trading > now:
        end_of_trading += pd.DateOffset(days=-1)
    return now.astimezone(None), end_of_trading.astimezone(None)


def last_history_from_doc(doc: Dict[str, Any]) -> datetime:
    """Момент времени UTC публикации данных о последних торгах, которая есть на MOEX ISS."""
    date = pd.Timestamp(doc["data"][0]["till"], tz=MOEX_TZ)
    return date.replace(**END_OF_TRADING).astimezone(None)


def get_last_history_date(db: str = DB, collection: str = MISC) -> datetime:
    """"Момент времени UTC после, которого не нужно обновлять данные."""
    mongodb = database.MongoDB(collection, db)
    doc = mongodb["last_date"]
    now, end_of_trading = now_and_end_of_trading_day()
    if doc is None or doc["timestamp"] < end_of_trading:
        data = apimoex.get_board_dates(
            mongo.HTTP_SESSION, board="TQBR", market="shares", engine="stock"
        )
        doc = dict(data=data, timestamp=now)
        mongodb["last_date"] = doc
        logging.info(f"Последняя дата с историей: {last_history_from_doc(doc).date()}")
    return last_history_from_doc(doc)
