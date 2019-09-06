"""Абстрактный менеджер данных - предоставляет локальные данные и следит за их обновлением."""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

import aiomoex
import numpy as np
import pandas as pd
import pymongo
import requests

from poptimizer.config import POptimizerError
from poptimizer.store import mongo
from poptimizer.store.utils import DATE

# Название базы для хранения данных
DB = "data"

# Часовой пояс MOEX
MOEX_TZ = "Europe/Moscow"

# Торги заканчиваются в 19.00, но данные публикуются 19.45
END_OF_TRADING = dict(hour=19, minute=45, second=0, microsecond=0, nanosecond=0)


async def get_board_dates() -> list:
    """Удалить."""
    async with aiomoex.ISSClientSession():
        return await aiomoex.get_board_dates()


def download_last_history() -> datetime:
    """Последняя дата торгов, которая есть на MOEX ISS."""
    dates = asyncio.run(get_board_dates())
    date = pd.Timestamp(dates[0]["till"], tz=MOEX_TZ)
    logging.info(f"Последняя дата с историей: {date.date()}")
    return date.replace(**END_OF_TRADING).astimezone(None)


def end_of_trading_day() -> datetime:
    """Конец последнего торгового дня в UTC."""
    now = pd.Timestamp.now(MOEX_TZ)
    end_of_trading = now.replace(**END_OF_TRADING)
    if end_of_trading > now:
        end_of_trading += pd.DateOffset(days=-1)
    return end_of_trading.astimezone(None)


def update_timestamp() -> datetime:
    """"Момент времени UTC после, которого не нужно обновлять данные."""
    utils_collection = mongo.CLIENT[DB]["utils"]
    last_history = utils_collection.find_one({"_id": "last_date"})
    end_of_trading = end_of_trading_day()
    if last_history is None or last_history["timestamp"] < end_of_trading:
        last_history = dict(_id="last_date", timestamp=download_last_history())
        utils_collection.replace_one({"_id": "last_date"}, last_history, upsert=True)
    return last_history["timestamp"]


class AbstractManager(ABC):
    """Организует создание, обновление и предоставление локальных данных."""

    def __init__(
        self,
        collection: str,
        db: str = DB,
        client: pymongo.MongoClient = mongo.CLIENT,
        create_from_scratch: bool = False,
        validate_last: bool = True,
        index: str = DATE,
        unique_index: bool = True,
        ascending_index: bool = True,
        session: requests.Session = mongo.SESSION,
    ):
        """Данные хранятся в MongoDB и извлекаются в виде DataFrame.

        Сохраняемые данные представляются в виде следующего документа:
        {
            _id: str
            data: DataFrame.to_dict(orient="records"),
            timestamp: datetime.datetime
        }

        :param collection:
            Коллекция в которой хранятся данные.
        :param db:
            База данных в которой хранятся данные.
        :param client:
            Подключенный клиент MongoDB.
        :param create_from_scratch:
            Нужно ли удалять данные при каждом обновлении.
        :param validate_last:
            Нужно ли при обновлении проверять только последнее значение или все значения.
        :param index:
            Наименование колонки для индекса.
        :param unique_index:
            Нужно ли тестировать индекс данных на уникальность.
        :param ascending_index:
            Нужно ли тестировать индекс данных на возрастание.
        :param session:
            Сессия для обновления данных по интернет.
        """
        self._collection = client[db][collection]
        self._index = index
        self._create_from_scratch = create_from_scratch
        self._validate_last = validate_last
        self._unique_index = unique_index
        self._ascending_index = ascending_index
        self._session = session

    def __getitem__(self, item: str):
        """Получение соответствующего элемента из базы."""
        timestamp = update_timestamp()
        doc = self._collection.find_one({"_id": item})
        if doc is None:
            doc = self.create(item)
        elif doc["timestamp"] < timestamp:
            if self._create_from_scratch:
                doc = self.create(item)
            else:
                doc = self.update(doc)
        df = pd.DataFrame(doc["data"]).set_index(self._index)
        self._validate_index(item, df)
        return df

    def _validate_index(self, item: str, df: pd.DataFrame):
        """Проверяет индекс данных с учетом настроек."""
        if self._unique_index and not df.index.is_unique:
            raise POptimizerError(
                f"Индекс {self._collection.full_name}.{item} не уникальный"
            )
        if self._ascending_index and not df.index.is_monotonic_increasing:
            raise POptimizerError(
                f"Индекс {self._collection.full_name}.{item} не возрастает"
            )

    def create(self, item: str) -> Dict[str, Any]:
        """Создает локальные данные с нуля или перезаписывает существующие.

        :param item:
            Наименование данных.
        """
        logging.info(f"Создание данных {self._collection.full_name}.{item}")
        data = self._download(item, None)
        doc = dict(_id=item, data=data, timestamp=datetime.utcnow())
        self._collection.replace_one({"_id": item}, doc, upsert=True)
        logging.info(f"Данные обновлены {self._collection.full_name}.{item}")
        return doc

    def update(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Обновляет локальные данные.

        Во время обновления проверяется стыковку новых данных с существующими.
        """
        item = doc["_id"]
        data = doc["data"]
        last_index = data[-1][self._index]
        logging.info(f"Обновление данных {self._collection.full_name}.{item}")
        data_new = self._download(item, last_index)
        self._validate_new(item, data, data_new)
        if self._validate_last:
            doc = dict(
                _id=item, data=data.extend(data_new[1:]), timestamp=datetime.utcnow()
            )
        else:
            doc = dict(_id=item, data=data_new, timestamp=datetime.utcnow())
        self._collection.replace_one({"_id": item}, doc)
        logging.info(f"Данные обновлены {self._collection.full_name}.{item}")
        return doc

    def _validate_new(
        self, item: str, data: List[Dict[str, Any]], data_new: List[Dict[str, Any]]
    ):
        """Проверяет соответствие старых и новых данных."""
        if self._validate_last:
            data = data[-1:]
            data_new = data_new[:1]
        if len(data) != len(data_new):
            raise POptimizerError(
                f"Данные {self._collection.full_name}.{item} не соответствуют обновлению по длине:"
                f"Старая:\n{len(data)}\n"
                f"Новая:\n{len(data_new)}\n"
            )
        for old, new in zip(data, data_new):
            for col in new:
                not_float_not_eq = (
                    not isinstance(old[col], float) and old[col] != new[col]
                )
                float_not_eq = isinstance(old[col], float) and not np.allclose(
                    old[col], new[col]
                )
                if not_float_not_eq or float_not_eq:
                    raise POptimizerError(
                        f"Данные {self._collection.full_name}.{item} не соответствуют обновлению:"
                        f"Старые значения:\n{old}\n"
                        f"Новые значения:\n{new}\n"
                    )

    @abstractmethod
    def _download(self, item: str, last_index: Optional[Any]) -> List[Dict[str, Any]]:
        """Загружает необходимые данные из внешних источников.

        :param item:
            Наименования данных.
        :param last_index:
            Если None, то скачиваются все данные. Если присутствует последние значение индекса,
            то для ускорения данные загружаются начиная с этого значения для инкрементального обновления.
        :return:
            Список словарей в формате DataFrame.to_dict("records").
        """


def data_formatter(
    data: List[Dict[str, Any]], formatters: Dict[str, Callable]
) -> List[Dict[str, Any]]:
    """Форматирует данные с учетом установок.

    :param data:
        Список словарей в формате DataFrame.to_dict("records").
    :param formatters:
        Словарь с функциями форматирования.
    :return:
       Отформатированный список словарей в формате.
    """
    for row in data:
        for col, formatter in formatters:
            row[col] = formatter(row[col])
    return data
